"""Hybrid retrieval: combine dense and keyword rankings with Reciprocal Rank Fusion (RRF).

``HybridRetriever.retrieve`` runs the stages that its ``mode`` names. Each stage is separate,
so the same code path serves the ablations in B7 (decision D3).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.vector_store import StoredChunk, VectorStore

Mode = Literal["dense", "bm25", "hybrid", "hybrid_rerank"]


class QueryEmbedder(Protocol):
    """The part of the embedder that retrieval needs."""

    def embed_query(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class RetrievalHit:
    """One chunk in a result, with the score of the stage that ranked it."""

    chunk: StoredChunk
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    """The hits for one query, best first."""

    hits: list[RetrievalHit]


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
    """Retrieves chunks by dense search, BM25, or both fused with RRF."""

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
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._keyword_index = keyword_index
        self._mode = mode
        self._dense_top_k = dense_top_k
        self._bm25_top_k = bm25_top_k
        self._rrf_k = rrf_k
        self._fused_top_k = fused_top_k
        # BM25 is built from the stored embed_text, so keyword search sees what the vectors saw.
        self._keyword_index.build(store.indexed_texts())

    def retrieve(self, query: str) -> RetrievalResult:
        if self._mode == "dense":
            ranking = self._dense_ranking(query)
        elif self._mode == "bm25":
            ranking = self._keyword_index.search(query, self._bm25_top_k)
        elif self._mode == "hybrid":
            ranking = rrf_fuse([self._dense_ids(query), self._keyword_ids(query)], self._rrf_k)
        else:
            raise NotImplementedError("hybrid_rerank arrives with the reranker (substep 4)")
        return RetrievalResult(hits=self._hits(ranking[: self._fused_top_k]))

    def _dense_ranking(self, query: str) -> list[tuple[str, float]]:
        return rrf_fuse([self._dense_ids(query)], self._rrf_k)

    def _dense_ids(self, query: str) -> list[str]:
        vector = self._embedder.embed_query(query)
        return [chunk.identifier for chunk in self._store.query(vector, self._dense_top_k)]

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
