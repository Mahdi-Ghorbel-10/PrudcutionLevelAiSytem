import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_script() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "board_sync.py"
    spec = importlib.util.spec_from_file_location("board_sync", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


board_sync = _load_script()

BOARD = """# Board

| Step | Task | Status | Builder | Reviewer | PR | quiz_ready | Notes |
|---|---|---|---|---|---|---|---|
| B1 | Scaffolding | merged | claude-code | zed | #1 | true | CI green |
| B2 | Ingestion | todo | — | — | — | false |  |
"""


def _pr(
    branch: str = "b2-ingestion",
    labels: list[str] | None = None,
    state: str = "open",
    merged: bool = False,
) -> dict[str, object]:
    return {
        "number": 5,
        "state": state,
        "merged": merged,
        "head": {"ref": branch},
        "labels": [{"name": name} for name in labels or []],
    }


def _no_pr(branch: str) -> bool:
    return False


def _no_spec(branch: str, step: str) -> str | None:
    return None


def _no_files(before: str, after: str) -> list[str]:
    return []


def test_set_cells_changes_only_named_cells() -> None:
    text = board_sync.set_cells(BOARD, "B2", {"status": "review", "pr": "#3"})
    assert "| B2 | Ingestion | review | — | — | #3 | false |  |" in text.split("\n")
    assert "| B1 | Scaffolding | merged | claude-code | zed | #1 | true | CI green |" in text


def test_set_cells_is_idempotent() -> None:
    once = board_sync.set_cells(BOARD, "B2", {"status": "doing"})
    assert board_sync.set_cells(once, "B2", {"status": "doing"}) == once


def test_set_cells_escapes_pipes_in_value() -> None:
    text = board_sync.set_cells(BOARD, "B2", {"notes": "a|b"})
    assert "| a\\|b |" in text


def test_set_cells_rejects_unknown_status() -> None:
    with pytest.raises(SystemExit):
        board_sync.set_cells(BOARD, "B2", {"status": "done"})


def test_set_cells_rejects_unknown_column() -> None:
    with pytest.raises(SystemExit):
        board_sync.set_cells(BOARD, "B2", {"owner": "zed"})


def test_set_cells_rejects_missing_step() -> None:
    with pytest.raises(SystemExit):
        board_sync.set_cells(BOARD, "B99", {"status": "doing"})


def test_step_from_branch() -> None:
    assert board_sync.step_from_branch("b2-ingestion") == "B2"
    assert board_sync.step_from_branch("b10-streaming") == "B10"
    assert board_sync.step_from_branch("board-sync") is None
    assert board_sync.step_from_branch("Dev") is None


def test_pr_opened_sets_review_and_defaults_reviewer_to_zed() -> None:
    payload = {"action": "opened", "pull_request": _pr()}
    changes = board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files)
    assert changes == [
        (
            "B2",
            {
                "status": "review",
                "builder": "claude-code",
                "reviewer": "zed",
                "pr": "#5",
                "notes": "",
            },
        )
    ]


def test_pr_opened_uses_reviewer_label() -> None:
    payload = {"action": "opened", "pull_request": _pr(labels=["reviewer:user"])}
    changes = board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files)
    assert changes[0][1]["reviewer"] == "user"


def test_reviewer_label_added_later() -> None:
    payload = {
        "action": "labeled",
        "label": {"name": "reviewer:user"},
        "pull_request": _pr(),
    }
    changes = board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files)
    assert changes == [("B2", {"reviewer": "user"})]


def test_pr_merged_sets_merged() -> None:
    payload = {"action": "closed", "pull_request": _pr(merged=True, state="closed")}
    changes = board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files)
    assert changes == [("B2", {"status": "merged", "pr": "#5", "notes": ""})]


def test_pr_closed_without_merge_changes_nothing() -> None:
    payload = {"action": "closed", "pull_request": _pr(state="closed")}
    assert board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files) == []


def test_non_build_branch_changes_nothing() -> None:
    payload = {"action": "opened", "pull_request": _pr(branch="board-sync")}
    assert board_sync.updates_for_event("pull_request", payload, _no_pr, _no_spec, _no_files) == []


def test_review_approved_sets_notes() -> None:
    payload = {
        "action": "submitted",
        "review": {"state": "approved"},
        "pull_request": _pr(),
    }
    changes = board_sync.updates_for_event(
        "pull_request_review", payload, _no_pr, _no_spec, _no_files
    )
    assert changes == [("B2", {"notes": "approved"})]


def test_review_changes_requested_sets_notes() -> None:
    payload = {
        "action": "submitted",
        "review": {"state": "changes_requested"},
        "pull_request": _pr(),
    }
    changes = board_sync.updates_for_event(
        "pull_request_review", payload, _no_pr, _no_spec, _no_files
    )
    assert changes == [("B2", {"notes": "changes requested"})]


def test_review_comment_changes_nothing() -> None:
    payload = {
        "action": "submitted",
        "review": {"state": "commented"},
        "pull_request": _pr(),
    }
    assert (
        board_sync.updates_for_event("pull_request_review", payload, _no_pr, _no_spec, _no_files)
        == []
    )


def test_push_with_open_pr_sets_review_and_clears_notes() -> None:
    payload = {"ref": "refs/heads/b2-ingestion", "commits": []}
    changes = board_sync.updates_for_event(
        "push", payload, lambda branch: True, _no_spec, _no_files
    )
    assert changes == [("B2", {"status": "review", "notes": ""})]


def test_first_push_with_approved_spec_sets_doing() -> None:
    payload = {"ref": "refs/heads/b2-ingestion", "commits": []}
    changes = board_sync.updates_for_event(
        "push", payload, _no_pr, lambda branch, step: "approved", _no_files
    )
    assert changes == [("B2", {"status": "doing", "builder": "claude-code"})]


def test_first_push_with_draft_spec_changes_nothing() -> None:
    payload = {"ref": "refs/heads/b2-ingestion", "commits": []}
    changes = board_sync.updates_for_event(
        "push", payload, _no_pr, lambda branch, step: "draft", _no_files
    )
    assert changes == []


def test_quiz_file_on_dev_sets_quiz_ready() -> None:
    payload = {"ref": "refs/heads/Dev", "before": "a1", "after": "b2"}

    def files(before: str, after: str) -> list[str]:
        assert (before, after) == ("a1", "b2")
        return ["quizzes/phase-1/B2-ingestion.md", "README.md"]

    changes = board_sync.updates_for_event("push", payload, _no_pr, _no_spec, files)
    assert changes == [("B2", {"quiz_ready": "true"})]


def test_push_to_dev_without_quiz_changes_nothing() -> None:
    payload = {"ref": "refs/heads/Dev", "before": "a1", "after": "b2"}

    def files(before: str, after: str) -> list[str]:
        return ["PLAN.md"]

    assert board_sync.updates_for_event("push", payload, _no_pr, _no_spec, files) == []
