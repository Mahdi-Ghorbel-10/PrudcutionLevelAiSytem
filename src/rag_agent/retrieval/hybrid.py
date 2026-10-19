"""Hybrid retrieval: combine dense and keyword rankings with Reciprocal Rank Fusion (RRF)."""

from collections.abc import Sequence


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
