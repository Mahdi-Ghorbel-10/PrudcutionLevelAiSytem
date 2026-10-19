import asyncio
from typing import Any

import pytest

from rag_agent.retrieval.reranker import Reranker
from rag_agent.retrieval.vector_store import StoredChunk


class FakeScorer:
    """Scores each pair by how many words the chunk shares with the query."""

    def predict(self, sentences: list[tuple[str, str]], *, batch_size: int) -> Any:
        return [
            float(len(set(query.lower().split()) & set(text.lower().split())))
            for query, text in sentences
        ]


def _chunk(identifier: str, text: str) -> StoredChunk:
    return StoredChunk(identifier=identifier, text=text, source="a.md", page=None, heading_path="")


CANDIDATES = [
    _chunk("cafe", "The cafeteria serves lunch at noon."),
    _chunk("leave", "Parental leave is twelve weeks for every parent."),
    _chunk("expenses", "Expense claims need a receipt."),
]


def test_order_follows_the_scores() -> None:
    reranker = Reranker("unused", model=FakeScorer())

    ranked = reranker.rerank("how many weeks of parental leave", CANDIDATES, top_k=3)

    # "leave" shares three words with the query. The other two share none, so they keep order.
    assert [chunk.identifier for chunk, _ in ranked] == ["leave", "cafe", "expenses"]


def test_output_has_top_k_items() -> None:
    reranker = Reranker("unused", model=FakeScorer())

    ranked = reranker.rerank("parental leave", CANDIDATES, top_k=2)

    assert len(ranked) == 2


def test_scores_are_returned_with_their_chunks() -> None:
    reranker = Reranker("unused", model=FakeScorer())

    ranked = reranker.rerank("parental leave weeks", CANDIDATES, top_k=3)

    assert ranked[0] == (CANDIDATES[1], 3.0)
    assert all(isinstance(score, float) for _, score in ranked)


def test_no_candidates_gives_no_results() -> None:
    reranker = Reranker("unused", model=FakeScorer())

    assert reranker.rerank("anything", [], top_k=4) == []


def test_async_rerank_matches_sync() -> None:
    reranker = Reranker("unused", model=FakeScorer())
    query = "parental leave"

    async_result = asyncio.run(reranker.arerank(query, CANDIDATES, top_k=3))

    assert async_result == reranker.rerank(query, CANDIDATES, top_k=3)


@pytest.mark.slow
def test_real_cross_encoder_ranks_the_matching_passage_first() -> None:
    reranker = Reranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

    ranked = reranker.rerank("How many weeks is parental leave?", CANDIDATES, top_k=3)

    assert ranked[0][0].identifier == "leave"
