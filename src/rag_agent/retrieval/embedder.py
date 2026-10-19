"""Embed chunks with a local sentence-transformers model on CPU.

The embedder reads each chunk's ``embed_text``, not its raw ``text``, so vectors match the
text that BM25 indexes (decision D7).
"""

import asyncio
from typing import Any, Protocol, cast

from rag_agent.ingestion.chunker import Chunk


class Encoder(Protocol):
    """The part of a sentence-transformers model that the embedder uses."""

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> Any: ...


class Embedder:
    """Turns chunks into normalized vectors, in batches."""

    def __init__(self, model_name: str, batch_size: int, model: Encoder | None = None) -> None:
        self._batch_size = batch_size
        self._model = model if model is not None else _load_model(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [[float(value) for value in vector] for vector in vectors]

    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed each chunk's ``embed_text``."""
        return self.embed_texts([chunk.embed_text for chunk in chunks])

    async def aembed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Run ``embed_chunks`` in a worker thread, so async code is not blocked by the model."""
        return await asyncio.to_thread(self.embed_chunks, chunks)


def _load_model(model_name: str) -> Encoder:
    from sentence_transformers import SentenceTransformer

    # SentenceTransformer's encode overloads are wider than Encoder; the call used here matches.
    return cast(Encoder, SentenceTransformer(model_name, device="cpu"))
