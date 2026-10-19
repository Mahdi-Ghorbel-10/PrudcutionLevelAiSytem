from rag_agent.retrieval.hybrid import rrf_fuse


def test_fused_order_follows_hand_made_rankings() -> None:
    dense = ["a", "b", "c"]
    keyword = ["c", "d", "a"]

    fused = rrf_fuse([dense, keyword], k=60)

    # a: 1/61 + 1/63, c: 1/63 + 1/61, so a and c tie. b and d come after, with one list each.
    assert [identifier for identifier, _ in fused] == ["a", "c", "b", "d"]


def test_id_found_by_both_lists_beats_one_found_by_one_at_the_same_rank() -> None:
    dense = ["shared", "dense_only"]
    keyword = ["keyword_only", "shared"]

    fused = rrf_fuse([dense, keyword], k=60)

    scores = dict(fused)
    # "keyword_only" is rank 1 in one list, the same rank as "shared" in the keyword list.
    # "shared" is also found by the dense list (rank 1), so it beats "keyword_only".
    assert scores["shared"] > scores["keyword_only"]
    # "dense_only" is rank 2 in one list, so it trails both.
    assert scores["keyword_only"] > scores["dense_only"]
    assert fused[0][0] == "shared"


def test_score_is_the_sum_of_reciprocal_ranks() -> None:
    fused = dict(rrf_fuse([["a", "b"], ["b"]], k=10))

    assert fused["a"] == 1 / (10 + 1)
    assert fused["b"] == 1 / (10 + 2) + 1 / (10 + 1)


def test_empty_rankings_give_no_results() -> None:
    assert rrf_fuse([[], []], k=60) == []
