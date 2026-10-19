from rag_agent.ingestion.chunker import Chunk, chunk_documents
from rag_agent.ingestion.ids import chunk_id
from rag_agent.ingestion.loaders import Document

MD = "# Leave Policy\nTwelve weeks of paid leave.\n\nStaff with one year of service qualify."


def _chunks(text: str, source: str = "policy.md") -> list[Chunk]:
    return chunk_documents([Document(text, source, None)], 800, 100, True)


def test_same_input_gives_the_same_ids_across_runs() -> None:
    first = [chunk_id(chunk) for chunk in _chunks(MD)]
    second = [chunk_id(chunk) for chunk in _chunks(MD)]

    assert first == second
    assert all(len(identifier) == 64 for identifier in first)


def test_edited_text_gets_a_new_id() -> None:
    original = _chunks(MD)[0]
    edited = _chunks(MD.replace("Twelve weeks", "Sixteen weeks"))[0]

    assert chunk_id(original) != chunk_id(edited)


def test_same_text_in_another_source_gets_a_new_id() -> None:
    a = _chunks(MD, source="a.md")[0]
    b = _chunks(MD, source="b.md")[0]

    assert chunk_id(a) != chunk_id(b)


def test_separator_prevents_field_collisions() -> None:
    left = Chunk(text="c", source="ab", page=None, heading_path="", embed_text="c")
    right = Chunk(text="bc", source="a", page=None, heading_path="", embed_text="bc")

    assert chunk_id(left) != chunk_id(right)
