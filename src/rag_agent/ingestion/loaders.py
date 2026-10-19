"""Read source files into documents, one per PDF page.

Text and Markdown files are read as UTF-8. PDFs use pypdf and DOCX files use python-docx.
"""

from dataclasses import dataclass
from pathlib import Path

from docx import Document as DocxDocument
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


@dataclass(frozen=True)
class Document:
    """Text from one file, or from one page of a PDF."""

    text: str
    source: str
    page: int | None  # 1-based for PDF pages, None for formats without pages


SUPPORTED_SUFFIXES = frozenset({".txt", ".md", ".pdf", ".docx"})


def load_file(path: Path) -> list[Document]:
    """Load one supported file. Raises ``ValueError`` for an unsupported file type."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [Document(path.read_text(encoding="utf-8"), str(path), None)]
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".docx":
        return _load_docx(path)
    raise ValueError(f"Unsupported file type: {path}")


def _load_pdf(path: Path) -> list[Document]:
    reader = PdfReader(path)
    return [
        Document(page.extract_text() or "", str(path), number)
        for number, page in enumerate(reader.pages, start=1)
    ]


def _load_docx(path: Path) -> list[Document]:
    document = DocxDocument(str(path))
    text = "\n".join(_docx_line(paragraph) for paragraph in document.paragraphs)
    return [Document(text, str(path), None)]


def _docx_line(paragraph: Paragraph) -> str:
    """Return a paragraph as a line, with ``Heading N`` styles written as ``#`` headings."""
    style_name = paragraph.style.name if paragraph.style is not None else None
    style = style_name or ""
    if style.startswith("Heading ") and style.removeprefix("Heading ").isdigit():
        level = int(style.removeprefix("Heading "))
        return f"{'#' * level} {paragraph.text}"
    return paragraph.text
