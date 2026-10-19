from collections.abc import Sequence
from pathlib import Path

import pytest

from rag_agent.ingestion.chunker import Chunk
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.hybrid import HybridRetriever, Mode, Reranking, rrf_fuse
from rag_agent.retrieval.vector_store import StoredChunk, VectorStore

COUNT = 15
ZEBRA = 7  # the only chunk that contains the keyword "zebra"


class SpyEmbedder:
    """Returns a fixed one-hot query vector and counts the calls."""

    def __init__(self) -> None:
        self.calls = 0

    def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        vector = [0.0] * COUNT
        vector[0] = 1.0
        return vector


class SpyIndex(BM25Index):
    """A BM25 index that counts searches."""

    def __init__(self) -> None:
        super().__init__()
        self.searches = 0

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        self.searches += 1
        return super().search(query, k)


def _store(tmp_path: Path) -> VectorStore:
    store = VectorStore(tmp_path / "chroma", "test")
    chunks = []
    for i in range(COUNT):
        text = "Document mentions zebra." if i == ZEBRA else f"Document {i} about topic {i % 3}."
        chunks.append(
            Chunk(text=text, source="docs.md", page=None, heading_path="", embed_text=text)
        )
    vectors = [[1.0 if dim == i else 0.0 for dim in range(COUNT)] for i in range(COUNT)]
    store.upsert(chunks, vectors)
    return store


class RaisingEmbedder:
    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("embedder is down")


class ReversingReranker:
    """Puts the candidates in reverse order, so the test can see that the reranker ran."""

    def rerank(
        self, query: str, candidates: Sequence[StoredChunk], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        return [(chunk, float(i)) for i, chunk in enumerate(reversed(candidates))][:top_k]


class RaisingReranker:
    def rerank(
        self, query: str, candidates: Sequence[StoredChunk], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        raise RuntimeError("reranker is down")


def _retriever(
    store: VectorStore,
    embedder: SpyEmbedder | RaisingEmbedder,
    index: BM25Index,
    mode: Mode,
    fused_top_k: int = 10,
    reranker: Reranking | None = None,
) -> HybridRetriever:
    return HybridRetriever(
        store=store,
        embedder=embedder,
        keyword_index=index,
        mode=mode,
        dense_top_k=20,
        bm25_top_k=20,
        rrf_k=60,
        fused_top_k=fused_top_k,
        reranker=reranker,
        rerank_top_k=4,
    )


def test_bm25_mode_never_calls_the_embedder(tmp_path: Path) -> None:
    store = _store(tmp_path)
    embedder = SpyEmbedder()
    retriever = _retriever(store, embedder, BM25Index(), "bm25")

    result = retriever.retrieve("zebra")

    assert embedder.calls == 0
    assert result.hits[0].chunk.text == "Document mentions zebra."


def test_dense_mode_never_reads_bm25_results(tmp_path: Path) -> None:
    store = _store(tmp_path)
    index = SpyIndex()
    retriever = _retriever(store, SpyEmbedder(), index, "dense")

    retriever.retrieve("zebra")

    assert index.searches == 0


def test_dense_mode_puts_the_nearest_chunk_first(tmp_path: Path) -> None:
    store = _store(tmp_path)
    retriever = _retriever(store, SpyEmbedder(), BM25Index(), "dense")

    result = retriever.retrieve("anything")

    assert result.hits[0].chunk.text == "Document 0 about topic 0."


def test_hybrid_returns_the_rrf_top_ten(tmp_path: Path) -> None:
    store = _store(tmp_path)
    index = BM25Index()
    retriever = _retriever(store, SpyEmbedder(), index, "hybrid", fused_top_k=10)

    result = retriever.retrieve("zebra")

    dense_ids = [chunk.identifier for chunk in store.query([1.0] + [0.0] * (COUNT - 1), 20)]
    keyword_ids = [identifier for identifier, _ in index.search("zebra", 20)]
    expected = rrf_fuse([dense_ids, keyword_ids], k=60)[:10]

    assert len(result.hits) == 10
    assert [hit.chunk.identifier for hit in result.hits] == [i for i, _ in expected]
    assert [hit.score for hit in result.hits] == [score for _, score in expected]


def test_hybrid_lifts_the_keyword_match_into_the_results(tmp_path: Path) -> None:
    store = _store(tmp_path)
    retriever = _retriever(store, SpyEmbedder(), BM25Index(), "hybrid")

    result = retriever.retrieve("zebra")

    texts = [hit.chunk.text for hit in result.hits]
    assert "Document mentions zebra." in texts


def test_clean_run_reports_no_degraded_stages(tmp_path: Path) -> None:
    store = _store(tmp_path)
    retriever = _retriever(store, SpyEmbedder(), BM25Index(), "hybrid")

    assert retriever.retrieve("zebra").degraded == []


def test_embedder_failure_falls_back_to_bm25_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    retriever = _retriever(store, RaisingEmbedder(), BM25Index(), "hybrid")

    result = retriever.retrieve("zebra")

    assert result.degraded == ["embedder"]
    assert [hit.chunk.text for hit in result.hits] == ["Document mentions zebra."]


def test_reranker_failure_returns_the_rrf_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    index = BM25Index()
    rrf_only = _retriever(store, SpyEmbedder(), index, "hybrid").retrieve("zebra")
    retriever = _retriever(store, SpyEmbedder(), index, "hybrid_rerank", reranker=RaisingReranker())

    result = retriever.retrieve("zebra")

    assert result.degraded == ["reranker"]
    assert [hit.chunk.identifier for hit in result.hits] == [
        hit.chunk.identifier for hit in rrf_only.hits[:4]
    ]


def test_hybrid_rerank_uses_the_reranker_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    retriever = _retriever(
        store, SpyEmbedder(), BM25Index(), "hybrid_rerank", reranker=ReversingReranker()
    )

    result = retriever.retrieve("zebra")

    assert result.degraded == []
    assert len(result.hits) == 4
    assert result.hits[0].score == 0.0


def test_hybrid_rerank_without_a_reranker_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)

    with pytest.raises(ValueError, match="needs a reranker"):
        _retriever(store, SpyEmbedder(), BM25Index(), "hybrid_rerank")
