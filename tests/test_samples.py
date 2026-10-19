from pathlib import Path

import pytest

from rag_agent.ingestion.chunker import chunk_documents
from rag_agent.ingestion.ids import chunk_id
from rag_agent.ingestion.loaders import load_file
from rag_agent.ingestion.pipeline import find_files
from rag_agent.retrieval.bm25 import BM25Index

SAMPLES = Path(__file__).parents[1] / "data" / "samples"

# Each sample file has one rare keyword that appears nowhere else.
KEYWORD_TO_FILE = {
    "marigoldrequest": "leave-policy.md",
    "copperkettle": "expenses.txt",
    "meadowsprint": "vpn-setup.txt",
    "bluelantern": "onboarding.pdf",
    "quartzshield": "security.docx",
}


@pytest.fixture(scope="module")
def indexed() -> tuple[BM25Index, dict[str, str]]:
    """The BM25 index over the sample chunks, and each chunk ID's source file."""
    documents = [document for path in find_files(SAMPLES) for document in load_file(path)]
    chunks = chunk_documents(documents, 800, 100, embed_with_heading=True)
    index = BM25Index()
    index.build([(chunk_id(chunk), chunk.embed_text) for chunk in chunks])
    return index, {chunk_id(chunk): Path(chunk.source).name for chunk in chunks}


@pytest.mark.parametrize(("keyword", "filename"), KEYWORD_TO_FILE.items())
def test_each_rare_keyword_finds_its_file_first(
    indexed: tuple[BM25Index, dict[str, str]], keyword: str, filename: str
) -> None:
    index, source_name = indexed

    results = index.search(keyword, k=3)

    assert results, f"no BM25 result for {keyword}"
    assert source_name[results[0][0]] == filename


def test_all_sample_files_are_found() -> None:
    names = {path.name for path in find_files(SAMPLES)}

    assert names == set(KEYWORD_TO_FILE.values())
