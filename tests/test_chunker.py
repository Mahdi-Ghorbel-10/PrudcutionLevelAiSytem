from rag_agent.ingestion.chunker import Chunk, chunk_documents
from rag_agent.ingestion.loaders import Document

NESTED_MD = """\
# Leave Policy
Intro text.
## Parental leave
Twelve weeks of paid leave.
### Eligibility
Staff with one year of service.
## Sick leave
Five days a year.
"""


def _chunk(text: str, size: int = 800, overlap: int = 100, heading: bool = True) -> list[Chunk]:
    documents = [Document(text, "policy.md", None)]
    return chunk_documents(documents, size, overlap, heading)


def test_keeps_source_and_page() -> None:
    documents = [
        Document("First page text.", "manual.pdf", 1),
        Document("Second.", "manual.pdf", 2),
    ]

    chunks = chunk_documents(documents, 800, 100, True)

    assert [(c.source, c.page) for c in chunks] == [("manual.pdf", 1), ("manual.pdf", 2)]


def test_every_chunk_is_within_the_size_limit() -> None:
    long_text = " ".join(f"word{i:03d}." for i in range(300))

    chunks = _chunk(long_text, size=120, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 120 for chunk in chunks)


def test_long_sentence_without_spaces_is_cut_by_size() -> None:
    chunks = _chunk("x" * 250, size=100, overlap=10)

    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert "".join(chunk.text[:90] for chunk in chunks).startswith("x" * 90)


def test_consecutive_chunks_overlap() -> None:
    text = " ".join(f"word{i:03d}." for i in range(200))

    chunks = _chunk(text, size=80, overlap=30)

    assert len(chunks) > 2
    for previous, following in zip(chunks, chunks[1:], strict=False):
        first_word = following.text.split()[0]
        assert first_word in previous.text


def test_heading_path_follows_nested_headings() -> None:
    chunks = _chunk(NESTED_MD, heading=True)

    paths = {chunk.text: chunk.heading_path for chunk in chunks}
    assert paths["Intro text."] == "Leave Policy"
    assert paths["Twelve weeks of paid leave."] == "Leave Policy > Parental leave"
    assert paths["Staff with one year of service."] == "Leave Policy > Parental leave > Eligibility"
    assert paths["Five days a year."] == "Leave Policy > Sick leave"


def test_embed_text_starts_with_heading_path_when_flag_is_on() -> None:
    chunks = _chunk(NESTED_MD, heading=True)

    sick = next(chunk for chunk in chunks if chunk.text == "Five days a year.")
    assert sick.embed_text == "Leave Policy > Sick leave\nFive days a year."


def test_embed_text_is_the_raw_text_when_flag_is_off() -> None:
    chunks = _chunk(NESTED_MD, heading=False)

    assert all(chunk.embed_text == chunk.text for chunk in chunks)


def test_embed_text_is_the_raw_text_above_any_heading() -> None:
    chunks = _chunk("Preface with no heading.", heading=True)

    assert chunks[0].heading_path == ""
    assert chunks[0].embed_text == "Preface with no heading."
