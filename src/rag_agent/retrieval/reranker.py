"""Rerank candidate chunks with a cross-encoder: one score per (query, chunk) pair.

A cross-encoder reads the query and the chunk together, so it is slower than the embedder
but more accurate. It runs on the few candidates that hybrid retrieval returns.
"""

import asyncio
from collections.abc import Sequence
from typing import Any, Protocol, cast

from rag_agent.retrieval.vector_store import StoredChunk


class Scorer(Protocol):
    """The part of a sentence-transformers CrossEncoder that the reranker uses."""

    def predict(self, sentences: list[tuple[str, str]], *, batch_size: int) -> Any: ...


class Reranker:
    """Scores candidates against the query and keeps the best ``top_k``."""

    def __init__(self, model_name: str, batch_size: int = 16, model: Scorer | None = None) -> None:
        self._batch_size = batch_size
        self._model = model if model is not None else _load_model(model_name)

    def rerank(
        self, query: str, candidates: Sequence[StoredChunk], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        """Return up to ``top_k`` ``(chunk, score)`` pairs, best first."""
        if not candidates:
            return []
        scores = self._model.predict(
            [(query, chunk.text) for chunk in candidates],
            batch_size=self._batch_size,
        )
        scored = [(chunk, float(score)) for chunk, score in zip(candidates, scores, strict=True)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    async def arerank(
        self, query: str, candidates: Sequence[StoredChunk], top_k: int
    ) -> list[tuple[StoredChunk, float]]:
        """Run ``rerank`` in a worker thread, so async code is not blocked by the model."""
        return await asyncio.to_thread(self.rerank, query, candidates, top_k)


def _load_model(model_name: str) -> Scorer:
    from sentence_transformers import CrossEncoder

    # CrossEncoder.predict's signature is wider than Scorer; the call used here matches it.
    return cast(Scorer, CrossEncoder(model_name, device="cpu"))
