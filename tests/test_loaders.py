from pathlib import Path

import pytest

from rag_agent.ingestion.loaders import load_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_txt_as_one_document(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("Plain text.\nSecond line.", encoding="utf-8")

    documents = load_file(path)

    assert len(documents) == 1
    assert documents[0].text == "Plain text.\nSecond line."
    assert documents[0].source == str(path)
    assert documents[0].page is None


def test_loads_md_as_one_document(tmp_path: Path) -> None:
    path = tmp_path / "guide.md"
    path.write_text("# Title\n\nBody text.", encoding="utf-8")

    documents = load_file(path)

    assert len(documents) == 1
    assert documents[0].text == "# Title\n\nBody text."
    assert documents[0].page is None


def test_loads_pdf_one_document_per_page() -> None:
    path = FIXTURES / "sample.pdf"

    documents = load_file(path)

    assert [doc.text for doc in documents] == ["Alpha page one", "Beta page two"]
    assert [doc.page for doc in documents] == [1, 2]
    assert all(doc.source == str(path) for doc in documents)


def test_loads_docx_text_in_paragraph_order() -> None:
    path = FIXTURES / "sample.docx"

    documents = load_file(path)

    assert len(documents) == 1
    assert documents[0].text == (
        "# Leave Policy\nStaff may take parental leave for up to twelve weeks.\n"
        "Requests go to the people team."
    )
    assert documents[0].page is None


def test_unsupported_file_type_fails(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_file(path)
