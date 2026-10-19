from rag_agent.retrieval.bm25 import BM25Index


def test_rare_query_word_ranks_its_chunk_first() -> None:
    index = BM25Index()
    index.build(
        [
            ("a", "Parental leave is twelve weeks for every parent."),
            ("b", "Sick leave is five days a year for every staff member."),
            ("c", "Office hours run from nine to five on weekdays."),
            ("d", "Expense claims need a receipt for every purchase."),
        ]
    )

    results = index.search("zebrafish", k=3)
    assert results == []

    results = index.search("twelve weeks", k=3)
    assert results[0][0] == "a"


def test_matches_text_that_is_only_in_the_heading_path() -> None:
    index = BM25Index()
    index.build(
        [
            ("a", "Leave Policy > Parental leave\nTwelve weeks of paid leave."),
            ("b", "Leave Policy > Sick leave\nFive days a year."),
        ]
    )

    results = index.search("parental", k=2)

    assert [identifier for identifier, _ in results] == ["a"]


def test_empty_index_returns_nothing() -> None:
    index = BM25Index()
    index.build([])

    assert index.search("anything", k=5) == []
    assert len(index) == 0


def test_respects_k() -> None:
    index = BM25Index()
    index.build([(str(i), f"shared word {i}") for i in range(5)])

    assert len(index.search("shared", k=2)) == 2


def test_rebuild_replaces_old_contents() -> None:
    index = BM25Index()
    index.build([("old", "alpha beta")])
    index.build([("new", "gamma delta")])

    assert index.search("alpha", k=5) == []
    assert [identifier for identifier, _ in index.search("gamma", k=5)] == ["new"]
