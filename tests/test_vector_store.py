from pathlib import Path

from rag_agent.ingestion.chunker import Chunk
from rag_agent.ingestion.ids import chunk_id
from rag_agent.retrieval.vector_store import VectorStore


def _chunk(text: str, embed_text: str | None = None) -> Chunk:
    return Chunk(
        text=text,
        source="policy.md",
        page=None,
        heading_path="Leave Policy",
        embed_text=embed_text or f"Leave Policy\n{text}",
    )


def test_upserting_the_same_chunks_twice_keeps_the_count(tmp_path: Path) -> None:
    store = VectorStore(tmp_path / "chroma", "test")
    chunks = [_chunk("First chunk."), _chunk("Second chunk.")]
    vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    store.upsert(chunks, vectors)
    store.upsert(chunks, vectors)

    assert store.count() == 2


def test_stored_document_is_the_raw_text_not_the_embed_text(tmp_path: Path) -> None:
    store = VectorStore(tmp_path / "chroma", "test")
    chunk = _chunk("Twelve weeks of paid leave.")

    store.upsert([chunk], [[0.1, 0.2, 0.3]])

    assert store.stored_texts([chunk_id(chunk)]) == {chunk_id(chunk): "Twelve weeks of paid leave."}


def test_existing_ids_reports_only_stored_chunks(tmp_path: Path) -> None:
    store = VectorStore(tmp_path / "chroma", "test")
    stored = _chunk("Stored chunk.")
    missing = _chunk("Not stored.")

    store.upsert([stored], [[0.1, 0.2, 0.3]])

    assert store.existing_ids([chunk_id(stored), chunk_id(missing)]) == {chunk_id(stored)}


def test_indexed_texts_returns_embed_text_for_each_chunk(tmp_path: Path) -> None:
    store = VectorStore(tmp_path / "chroma", "test")
    chunk = _chunk("Five days a year.", embed_text="Leave Policy > Sick leave\nFive days a year.")

    store.upsert([chunk], [[0.1, 0.2, 0.3]])

    assert store.indexed_texts() == [
        (chunk_id(chunk), "Leave Policy > Sick leave\nFive days a year.")
    ]
