import asyncio
from typing import Any

import numpy as np
import pytest

from rag_agent.ingestion.chunker import Chunk
from rag_agent.retrieval.embedder import Embedder


class FakeEncoder:
    """Records what it was asked to encode and returns fixed-size vectors."""

    def __init__(self, dimensions: int = 3) -> None:
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> Any:
        self.calls.append(list(sentences))
        return np.ones((len(sentences), self.dimensions))


def _chunk(text: str, embed_text: str) -> Chunk:
    return Chunk(text=text, source="a.md", page=None, heading_path="Leave", embed_text=embed_text)


def test_embedder_encodes_embed_text_not_raw_text() -> None:
    encoder = FakeEncoder()
    embedder = Embedder("unused", batch_size=8, model=encoder)
    chunks = [_chunk("Five days.", "Leave > Sick\nFive days.")]

    embedder.embed_chunks(chunks)

    assert encoder.calls == [["Leave > Sick\nFive days."]]


def test_embed_chunks_returns_one_vector_per_chunk() -> None:
    embedder = Embedder("unused", batch_size=8, model=FakeEncoder(dimensions=3))
    chunks = [_chunk("One.", "One."), _chunk("Two.", "Two.")]

    vectors = embedder.embed_chunks(chunks)

    assert vectors == [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]


def test_empty_input_skips_the_model() -> None:
    encoder = FakeEncoder()
    embedder = Embedder("unused", batch_size=8, model=encoder)

    assert embedder.embed_chunks([]) == []
    assert encoder.calls == []


def test_async_embedding_matches_sync() -> None:
    encoder = FakeEncoder()
    embedder = Embedder("unused", batch_size=8, model=encoder)
    chunks = [_chunk("One.", "One.")]

    vectors = asyncio.run(embedder.aembed_chunks(chunks))

    assert vectors == embedder.embed_chunks(chunks)


@pytest.mark.slow
def test_real_model_gives_384_dimensional_vectors() -> None:
    embedder = Embedder("BAAI/bge-small-en-v1.5", batch_size=8)
    chunks = [
        _chunk("Parental leave is twelve weeks.", "x"),
        _chunk("Sick leave is five days.", "y"),
    ]

    vectors = embedder.embed_chunks(chunks)

    assert len(vectors) == 2
    assert all(len(vector) == 384 for vector in vectors)
