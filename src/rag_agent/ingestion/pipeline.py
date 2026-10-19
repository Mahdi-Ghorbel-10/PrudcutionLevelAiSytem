"""Ingest files: load, chunk, embed the new chunks, store them, and rebuild the keyword index.

Chunk IDs come from content, so a chunk that is already stored is skipped and never embedded
again. Running the same ingest twice adds nothing the second time.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from rag_agent.ingestion.chunker import Chunk, chunk_documents
from rag_agent.ingestion.ids import chunk_id
from rag_agent.ingestion.loaders import SUPPORTED_SUFFIXES, load_file
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.embedder import Embedder
from rag_agent.retrieval.vector_store import VectorStore


@dataclass(frozen=True)
class IngestReport:
    """What one ingest run did."""

    files: int
    chunks_added: int
    chunks_skipped: int  # already stored, or repeated within this run


def find_files(path: Path) -> list[Path]:
    """Return the supported files at ``path``: the file itself, or every file under a folder."""
    if path.is_file():
        return [path]
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
    )


class IngestionPipeline:
    """Runs ingest for a path, and keeps the BM25 index in step with the store."""

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        keyword_index: BM25Index,
        chunk_size: int,
        chunk_overlap: int,
        embed_with_heading: bool,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._keyword_index = keyword_index
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embed_with_heading = embed_with_heading

    def run(self, path: Path) -> IngestReport:
        files = find_files(path)
        documents = [document for file in files for document in load_file(file)]
        chunks = chunk_documents(
            documents, self._chunk_size, self._chunk_overlap, self._embed_with_heading
        )
        new = self._new_chunks(chunks)
        self._store.upsert(new, self._embedder.embed_chunks(new))
        self.rebuild_keyword_index()
        return IngestReport(
            files=len(files),
            chunks_added=len(new),
            chunks_skipped=len(chunks) - len(new),
        )

    def rebuild_keyword_index(self) -> None:
        """Rebuild BM25 from every stored chunk's ``embed_text``. Call once at startup too."""
        self._keyword_index.build(self._store.indexed_texts())

    def _new_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Return the chunks not yet stored, keeping the first of any repeats in this run."""
        unique = _first_by_id(chunks)
        stored = self._store.existing_ids(list(unique))
        return [chunk for identifier, chunk in unique.items() if identifier not in stored]


def _first_by_id(chunks: Iterable[Chunk]) -> dict[str, Chunk]:
    unique: dict[str, Chunk] = {}
    for chunk in chunks:
        unique.setdefault(chunk_id(chunk), chunk)
    return unique
