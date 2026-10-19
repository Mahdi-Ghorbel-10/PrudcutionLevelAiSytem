"""Split documents into chunks that keep their source, page and heading path.

Text is split at Markdown headings first, then at blank lines, then at sentence ends. A piece
that is still too long is cut by size. Chunks are packed up to the size limit, and each chunk
starts with the last words of the previous one, so a sentence split across two chunks is
found in both.
"""

import re
from dataclasses import dataclass

from rag_agent.ingestion.loaders import Document

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
HEADING_SEPARATOR = " > "


@dataclass(frozen=True)
class Chunk:
    """A piece of a document, ready to embed and store."""

    text: str
    source: str
    page: int | None
    heading_path: str  # for example "Leave Policy > Parental leave"; empty above any heading
    embed_text: str  # the text the vectors and BM25 index are built from


def chunk_documents(
    documents: list[Document],
    chunk_size: int,
    chunk_overlap: int,
    embed_with_heading: bool,
) -> list[Chunk]:
    """Split documents into chunks no longer than ``chunk_size`` characters."""
    chunks: list[Chunk] = []
    headings: list[tuple[int, str]] = []
    current_source: str | None = None
    for document in documents:
        if document.source != current_source:
            headings = []
            current_source = document.source
        body: list[str] = []
        for line in document.text.splitlines():
            heading = HEADING.match(line)
            if heading is None:
                body.append(line)
                continue
            chunks.extend(
                _chunks_for_body(
                    body, document, headings, chunk_size, chunk_overlap, embed_with_heading
                )
            )
            body = []
            level = len(heading.group(1))
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, heading.group(2)))
        chunks.extend(
            _chunks_for_body(
                body, document, headings, chunk_size, chunk_overlap, embed_with_heading
            )
        )
    return chunks


def _chunks_for_body(
    lines: list[str],
    document: Document,
    headings: list[tuple[int, str]],
    chunk_size: int,
    chunk_overlap: int,
    embed_with_heading: bool,
) -> list[Chunk]:
    heading_path = HEADING_SEPARATOR.join(title for _, title in headings)
    return [
        _make_chunk(text, document, heading_path, embed_with_heading)
        for text in _split_text("\n".join(lines), chunk_size, chunk_overlap)
    ]


def _make_chunk(
    text: str, document: Document, heading_path: str, embed_with_heading: bool
) -> Chunk:
    if embed_with_heading and heading_path:
        embed_text = f"{heading_path}\n{text}"
    else:
        embed_text = text
    return Chunk(text, document.source, document.page, heading_path, embed_text)


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Pack paragraph and sentence pieces into chunks, starting each with the previous overlap."""
    chunks: list[str] = []
    current = ""
    for unit in _units(text, chunk_size):
        if not current:
            current = unit
        elif len(current) + 1 + len(unit) <= chunk_size:
            current = f"{current}\n{unit}"
        else:
            chunks.append(current)
            overlap = _overlap_tail(current, chunk_overlap)
            joined = f"{overlap}\n{unit}" if overlap else unit
            current = joined if len(joined) <= chunk_size else unit
    if current:
        chunks.append(current)
    return chunks


def _units(text: str, chunk_size: int) -> list[str]:
    """Split text into pieces of at most ``chunk_size``: paragraphs, then sentences, then slices."""
    units: list[str] = []
    for paragraph in PARAGRAPH_BREAK.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
            continue
        for sentence in SENTENCE_END.split(paragraph):
            units.extend(sentence[i : i + chunk_size] for i in range(0, len(sentence), chunk_size))
    return units


def _overlap_tail(text: str, chunk_overlap: int) -> str:
    """Return the last ``chunk_overlap`` characters, starting after a space where possible."""
    if chunk_overlap == 0:
        return ""
    tail = text[-chunk_overlap:]
    space = tail.find(" ")
    return tail[space + 1 :] if space != -1 else tail
