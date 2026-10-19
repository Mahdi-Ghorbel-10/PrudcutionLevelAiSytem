"""Hybrid retrieval: combine dense and keyword rankings with Reciprocal Rank Fusion (RRF).

``HybridRetriever.retrieve`` runs the stages that its ``mode`` names. Each stage is separate,
so the same code path serves the ablations in B7 (decision D3).

When a stage fails, the query still returns results. The failed stage is named in
``RetrievalResult.degraded``: the embedder falls back to BM25 alone, and the reranker falls back
to the RRF order (decision D4).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from rag_agent.config import RetrievalMode
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.vector_store import StoredChunk, VectorStore

Mode = RetrievalMode


class QueryEmbedder(Protocol):
    """The part of the embedder that retrieval needs."""

    def embed_query(self, text: str) -> list[float]: ...


class Reranking(Protocol):
    """The part of the reranker that retrieval needs."""

    def rerank(
        self, query: str, candidates: Sequence[StoredChunk], top_k: int
    ) -> list[tuple[StoredChunk, float]]: ...


@dataclass(frozen=True)
class RetrievalHit:
    """One chunk in a result, with the score of the stage that ranked it."""

    chunk: StoredChunk
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    """The hits for one query, best first. ``degraded`` names stages that failed (empty if none)."""

    hits: list[RetrievalHit]
    degraded: list[str] = field(default_factory=list)


def rrf_fuse(rankings: Sequence[Sequence[str]], k: int) -> list[tuple[str, float]]:
    """Fuse ranked lists of chunk IDs. Each ID scores ``sum(1 / (k + rank))`` over the lists.

    Ranks start at 1. An ID found by several lists gets a score from each, so it beats an ID
    found by one list at the same rank. Returns ``(id, score)`` pairs, best first.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, identifier in enumerate(ranking, start=1):
            scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class HybridRetriever:
    """Retrieves chunks by dense search, BM25, or both fused with RRF, then optionally reranks."""

    def __init__(
        self,
        store: VectorStore,
        embedder: QueryEmbedder,
        keyword_index: BM25Index,
        mode: Mode,
        dense_top_k: int,
        bm25_top_k: int,
        rrf_k: int,
        fused_top_k: int,
        reranker: Reranking | None = None,
        rerank_top_k: int = 4,
    ) -> None:
        if mode == "hybrid_rerank" and reranker is None:
            raise ValueError("mode hybrid_rerank needs a reranker")
        self._store = store
        self._embedder = embedder
        self._keyword_index = keyword_index
        self._mode = mode
        self._dense_top_k = dense_top_k
        self._bm25_top_k = bm25_top_k
        self._rrf_k = rrf_k
        self._fused_top_k = fused_top_k
        self._reranker = reranker
        self._rerank_top_k = rerank_top_k
        # BM25 is built from the stored embed_text, so keyword search sees what the vectors saw.
        self._keyword_index.build(store.indexed_texts())

    def retrieve(self, query: str) -> RetrievalResult:
        degraded: list[str] = []
        ranking = self._first_stage(query, degraded)
        hits = self._hits(ranking[: self._fused_top_k])
        if self._mode == "hybrid_rerank":
            hits = self._rerank(query, hits, degraded)
        return RetrievalResult(hits=hits, degraded=degraded)

    def _first_stage(self, query: str, degraded: list[str]) -> list[tuple[str, float]]:
        """Rank candidates with the stages the mode needs. Falls back to BM25 if embedding fails."""
        if self._mode == "bm25":
            return self._keyword_index.search(query, self._bm25_top_k)
        vector = self._embed(query, degraded)
        if vector is None:
            return self._keyword_index.search(query, self._bm25_top_k)
        dense_ids = [chunk.identifier for chunk in self._store.query(vector, self._dense_top_k)]
        if self._mode == "dense":
            return rrf_fuse([dense_ids], self._rrf_k)
        return rrf_fuse([dense_ids, self._keyword_ids(query)], self._rrf_k)

    def _embed(self, query: str, degraded: list[str]) -> list[float] | None:
        try:
            return self._embedder.embed_query(query)
        except Exception:  # any embedder failure degrades the query to BM25 alone
            degraded.append("embedder")
            return None

    def _rerank(
        self, query: str, hits: list[RetrievalHit], degraded: list[str]
    ) -> list[RetrievalHit]:
        if self._reranker is None:
            raise RuntimeError("hybrid_rerank without a reranker")
        try:
            ranked = self._reranker.rerank(query, [hit.chunk for hit in hits], self._rerank_top_k)
        except Exception:  # any reranker failure keeps the RRF order
            degraded.append("reranker")
            return hits[: self._rerank_top_k]
        return [RetrievalHit(chunk=chunk, score=score) for chunk, score in ranked]

    def _keyword_ids(self, query: str) -> list[str]:
        return [identifier for identifier, _ in self._keyword_index.search(query, self._bm25_top_k)]

    def _hits(self, ranking: list[tuple[str, float]]) -> list[RetrievalHit]:
        """Attach stored chunks to ranked IDs, in rank order. Missing IDs are skipped."""
        chunks = self._store.chunks_by_id([identifier for identifier, _ in ranking])
        return [
            RetrievalHit(chunk=chunks[identifier], score=score)
            for identifier, score in ranking
            if identifier in chunks
        ]
