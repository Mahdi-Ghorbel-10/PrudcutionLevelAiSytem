from pathlib import Path
from typing import Any

import numpy as np

from rag_agent.ingestion.pipeline import IngestionPipeline, find_files
from rag_agent.retrieval.bm25 import BM25Index
from rag_agent.retrieval.embedder import Embedder
from rag_agent.retrieval.vector_store import VectorStore

FIXTURES = Path(__file__).parent / "fixtures"


class CountingEncoder:
    """Counts how many sentences it was asked to embed, to prove skipped chunks are not embedded."""

    def __init__(self) -> None:
        self.embedded = 0

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> Any:
        self.embedded += len(sentences)
        return np.ones((len(sentences), 3))


def _pipeline(tmp_path: Path, encoder: CountingEncoder) -> tuple[IngestionPipeline, BM25Index]:
    store = VectorStore(tmp_path / "chroma", "test")
    keyword_index = BM25Index()
    pipeline = IngestionPipeline(
        store=store,
        embedder=Embedder("unused", batch_size=8, model=encoder),
        keyword_index=keyword_index,
        chunk_size=800,
        chunk_overlap=100,
        embed_with_heading=True,
    )
    return pipeline, keyword_index


def _write_docs(folder: Path) -> None:
    folder.mkdir()
    (folder / "leave.md").write_text(
        "# Leave Policy\n\nParental leave is twelve weeks.\n", encoding="utf-8"
    )
    (folder / "notes.txt").write_text("Office hours are nine to five.", encoding="utf-8")
    (folder / "ignored.csv").write_text("a,b", encoding="utf-8")


def test_second_run_on_the_same_folder_adds_nothing(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    _write_docs(docs)
    encoder = CountingEncoder()
    pipeline, _ = _pipeline(tmp_path, encoder)

    first = pipeline.run(docs)
    embedded_after_first = encoder.embedded
    second = pipeline.run(docs)

    assert first.files == 2
    assert first.chunks_added == 2
    assert second.chunks_added == 0
    assert second.chunks_skipped == 2
    assert encoder.embedded == embedded_after_first


def test_keyword_index_is_rebuilt_after_ingest(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    _write_docs(docs)
    pipeline, keyword_index = _pipeline(tmp_path, CountingEncoder())

    pipeline.run(docs)

    results = keyword_index.search("parental", k=1)
    assert len(results) == 1
    assert len(keyword_index) == 2


def test_ingests_a_single_file_and_its_word_is_findable(tmp_path: Path) -> None:
    pipeline, keyword_index = _pipeline(tmp_path, CountingEncoder())

    report = pipeline.run(FIXTURES / "sample.docx")

    assert report.files == 1
    assert report.chunks_added >= 1
    assert keyword_index.search("parental", k=1)


def test_find_files_keeps_only_supported_types(tmp_path: Path) -> None:
    _write_docs(tmp_path / "docs")

    names = [path.name for path in find_files(tmp_path / "docs")]

    assert names == ["leave.md", "notes.txt"]
