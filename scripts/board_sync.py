"""Update build-step rows on the board in COLLABORATION.md.

Manual mode (workflow_dispatch, or by hand):
    python3 scripts/board_sync.py COLLABORATION.md B2 status=merged notes="CI green"

Event mode (run by .github/workflows/board-sync.yml):
    python3 scripts/board_sync.py --event COLLABORATION.md
    Reads $GITHUB_EVENT_PATH and $GITHUB_EVENT_NAME. Uses `gh` and `git` for the
    open-PR and spec-status checks, so $GH_TOKEN and a fetched origin are needed.

Only the named cells change. Cells are split on unescaped pipes, so `\\|` inside
a value is safe. Running it again with the same values changes nothing.
"""

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROW = re.compile(r"^\|\s*(B\d+)\s*\|")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
# cells[0] is empty (before the first pipe), then Step and Task, then the columns below.
COLUMNS = {"status": 3, "builder": 4, "reviewer": 5, "pr": 6, "quiz_ready": 7, "notes": 8}
STATUSES = {"todo", "spec", "doing", "review", "merged", "blocked"}
REVIEWERS = {"zed", "user"}
BUILDER = "claude-code"
DEFAULT_REVIEWER = "zed"
QUIZ_FILE = re.compile(r"^quizzes/phase-\d+/(B\d+)-[^/]+\.md$")

Update = dict[str, str]
Change = tuple[str, Update]


def check(column: str, value: str) -> None:
    if column not in COLUMNS:
        raise SystemExit(f"error: unknown column {column!r}, use one of {sorted(COLUMNS)}")
    if column == "status" and value not in STATUSES:
        raise SystemExit(f"error: status must be one of {sorted(STATUSES)}, got {value!r}")
    if column == "reviewer" and value not in REVIEWERS:
        raise SystemExit(f"error: reviewer must be one of {sorted(REVIEWERS)}, got {value!r}")
    if column == "quiz_ready" and value not in {"true", "false"}:
        raise SystemExit(f"error: quiz_ready must be true or false, got {value!r}")


def set_cells(text: str, step: str, updates: Update) -> str:
    for column, value in updates.items():
        check(column, value)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        match = ROW.match(line)
        if not match or match.group(1) != step:
            continue
        cells = UNESCAPED_PIPE.split(line)
        changed = False
        for column, value in updates.items():
            escaped = value.replace("|", "\\|")
            index = COLUMNS[column]
            if cells[index].strip() != escaped:
                cells[index] = f" {escaped} "
                changed = True
        if changed:
            lines[i] = "|".join(cells)
        return "\n".join(lines)
    raise SystemExit(f"error: no board row for {step}")


def step_from_branch(branch: str) -> str | None:
    match = re.match(r"^b(\d+)-", branch)
    return f"B{match.group(1)}" if match else None


def label_names(pr: dict[str, object]) -> list[str]:
    labels = pr["labels"]
    assert isinstance(labels, list)
    return [label["name"] for label in labels]


def reviewer_from_labels(labels: list[str]) -> str:
    for label in labels:
        if label.startswith("reviewer:"):
            return label.removeprefix("reviewer:")
    return DEFAULT_REVIEWER


def pull_request_changes(payload: dict[str, object]) -> list[Change]:
    pr = payload["pull_request"]
    assert isinstance(pr, dict)
    head = pr["head"]
    assert isinstance(head, dict)
    step = step_from_branch(head["ref"])
    action = payload["action"]
    if step is None:
        return []
    number = f"#{pr['number']}"
    if action in {"opened", "reopened", "ready_for_review"}:
        reviewer = reviewer_from_labels(label_names(pr))
        return [
            (
                step,
                {
                    "status": "review",
                    "builder": BUILDER,
                    "reviewer": reviewer,
                    "pr": number,
                    "notes": "",
                },
            )
        ]
    if action == "labeled" and pr["state"] == "open":
        label = payload["label"]
        assert isinstance(label, dict)
        name = str(label["name"])
        if name.startswith("reviewer:"):
            return [(step, {"reviewer": name.removeprefix("reviewer:")})]
        return []
    if action == "closed" and pr.get("merged"):
        return [(step, {"status": "merged", "pr": number, "notes": ""})]
    return []


def review_changes(payload: dict[str, object]) -> list[Change]:
    pr = payload["pull_request"]
    review = payload["review"]
    assert isinstance(pr, dict)
    assert isinstance(review, dict)
    head = pr["head"]
    assert isinstance(head, dict)
    step = step_from_branch(head["ref"])
    if step is None or payload["action"] != "submitted":
        return []
    if review["state"] == "approved":
        return [(step, {"notes": "approved"})]
    if review["state"] == "changes_requested":
        return [(step, {"notes": "changes requested"})]
    return []


def push_changes(
    payload: dict[str, object],
    has_open_pr: Callable[[str], bool],
    spec_status: Callable[[str, str], str | None],
    changed_files: Callable[[str, str], list[str]],
) -> list[Change]:
    ref = str(payload["ref"]).removeprefix("refs/heads/")
    if ref == "Dev":
        steps: list[str] = []
        for path in changed_files(str(payload["before"]), str(payload["after"])):
            match = QUIZ_FILE.match(path)
            if match and match.group(1) not in steps:
                steps.append(match.group(1))
        return [(step, {"quiz_ready": "true"}) for step in steps]
    step = step_from_branch(ref)
    if step is None:
        return []
    if has_open_pr(ref):
        return [(step, {"status": "review", "notes": ""})]
    if spec_status(ref, step) in {"approved", "building"}:
        return [(step, {"status": "doing", "builder": BUILDER})]
    return []


def updates_for_event(
    name: str,
    payload: dict[str, object],
    has_open_pr: Callable[[str], bool],
    spec_status: Callable[[str, str], str | None],
    changed_files: Callable[[str, str], list[str]],
) -> list[Change]:
    if name == "pull_request":
        return pull_request_changes(payload)
    if name == "pull_request_review":
        return review_changes(payload)
    if name == "push":
        return push_changes(payload, has_open_pr, spec_status, changed_files)
    return []


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return result.stdout


def has_open_pr(branch: str) -> bool:
    out = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return bool(json.loads(out))


def changed_files(before: str, after: str) -> list[str]:
    return git("diff", "--name-only", before, after).splitlines()


def spec_status(branch: str, step: str) -> str | None:
    files = git("ls-tree", "-r", "--name-only", f"origin/{branch}", "--", "specs/")
    matches = [path for path in files.splitlines() if path.startswith(f"specs/{step}-")]
    if not matches:
        return None
    for line in git("show", f"origin/{branch}:{matches[0]}").splitlines():
        if line.startswith("Status:"):
            words = line.removeprefix("Status:").split()
            return words[0] if words else None
    return None


def event_mode(path: Path) -> None:
    payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    changes = updates_for_event(
        os.environ["GITHUB_EVENT_NAME"], payload, has_open_pr, spec_status, changed_files
    )
    text = path.read_text(encoding="utf-8")
    for step, updates in changes:
        text = set_cells(text, step, updates)
        print(f"{step}: {updates}")
    if not changes:
        print("No board change for this event.")
    path.write_text(text, encoding="utf-8")


def manual_mode(path: Path, step: str, pairs: list[str]) -> None:
    updates: Update = {}
    for pair in pairs:
        column, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"error: expected column=value, got {pair!r}")
        updates[column] = value
    path.write_text(set_cells(path.read_text(encoding="utf-8"), step, updates), encoding="utf-8")


def main(argv: list[str]) -> None:
    if argv[:1] == ["--event"] and len(argv) == 2:
        event_mode(Path(argv[1]))
    elif len(argv) >= 3:
        manual_mode(Path(argv[0]), argv[1], argv[2:])
    else:
        raise SystemExit(
            "usage: board_sync.py <COLLABORATION.md> <step> <column=value>...\n"
            "       board_sync.py --event <COLLABORATION.md>"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
