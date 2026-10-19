"""Chroma store for chunks. Writes use ``upsert``, so re-ingesting the same files is a no-op."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from rag_agent.ingestion.chunker import Chunk
from rag_agent.ingestion.ids import chunk_id

NO_PAGE = 0  # PDF pages start at 1, so 0 marks a chunk with no page (Chroma metadata has no null)


@dataclass(frozen=True)
class StoredChunk:
    """A chunk as read back from the store. ``text`` is the raw text, not the embedded text."""

    identifier: str
    text: str
    source: str
    page: int | None
    heading_path: str


class VectorStore:
    """A persistent Chroma collection of chunk vectors and their raw text."""

    def __init__(self, path: Path, collection_name: str) -> None:
        client = chromadb.PersistentClient(path=str(path))
        self._collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,  # vectors come from the embedder, not from Chroma
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Store each chunk's raw text, with the vector built from its ``embed_text``."""
        if not chunks:
            return
        vectors: list[Sequence[float] | Sequence[int]] = [vector for vector in embeddings]
        self._collection.upsert(
            ids=[chunk_id(chunk) for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=[
                {
                    "source": chunk.source,
                    "page": chunk.page or NO_PAGE,
                    "heading_path": chunk.heading_path,
                    "embed_text": chunk.embed_text,
                }
                for chunk in chunks
            ],
        )

    def existing_ids(self, ids: list[str]) -> set[str]:
        """Return which of the given IDs are already stored."""
        if not ids:
            return set()
        return set(self._collection.get(ids=ids, include=[])["ids"])

    def stored_texts(self, ids: list[str]) -> dict[str, str]:
        """Return the raw stored text for each ID that is present."""
        if not ids:
            return {}
        result = self._collection.get(ids=ids, include=["documents"])
        return {
            identifier: document
            for identifier, document in zip(result["ids"], result["documents"] or [], strict=True)
        }

    def query(self, embedding: list[float], k: int) -> list[StoredChunk]:
        """Return the ``k`` stored chunks nearest to ``embedding``, nearest first."""
        if k <= 0 or self.count() == 0:
            return []
        query_vectors: list[Sequence[float] | Sequence[int]] = [embedding]
        result = self._collection.query(
            query_embeddings=query_vectors,
            n_results=min(k, self.count()),
            include=["documents", "metadatas"],
        )
        documents = (result["documents"] or [[]])[0]
        metadatas = (result["metadatas"] or [[]])[0]
        return [
            _stored(identifier, document, metadata)
            for identifier, document, metadata in zip(
                result["ids"][0], documents, metadatas, strict=True
            )
        ]

    def chunks_by_id(self, ids: list[str]) -> dict[str, StoredChunk]:
        """Return the stored chunk for each ID that is present."""
        if not ids:
            return {}
        result = self._collection.get(ids=ids, include=["documents", "metadatas"])
        return {
            identifier: _stored(identifier, document, metadata)
            for identifier, document, metadata in zip(
                result["ids"],
                result["documents"] or [],
                result["metadatas"] or [],
                strict=True,
            )
        }

    def indexed_texts(self) -> list[tuple[str, str]]:
        """Return ``(id, embed_text)`` for every stored chunk. BM25 is built from these."""
        result = self._collection.get(include=["metadatas"])
        return [
            (identifier, str((metadata or {})["embed_text"]))
            for identifier, metadata in zip(result["ids"], result["metadatas"] or [], strict=True)
        ]

    def count(self) -> int:
        return self._collection.count()


def _stored(
    identifier: str, document: str | None, metadata: Mapping[str, Any] | None
) -> StoredChunk:
    meta = metadata or {}
    page = int(meta["page"])
    return StoredChunk(
        identifier=identifier,
        text=document or "",
        source=str(meta["source"]),
        page=None if page == NO_PAGE else page,
        heading_path=str(meta["heading_path"]),
    )
