"""Set one build step's status on the board in COLLABORATION.md.

Usage: python3 scripts/board_sync.py COLLABORATION.md B1 merged

Only the Status cell of the matching row changes. Other cells are kept as they are.
Cells are split on unescaped pipes, so `\\|` inside a task name is safe.
Running it again with the same status changes nothing.
"""

import re
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*(B\d+)\s*\|")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
# cells[0] is empty (before the first pipe), then Step, Task, Status.
STATUS_CELL = 3
ALLOWED = {"todo", "spec", "doing", "review", "merged", "blocked"}


def set_status(text: str, step: str, status: str) -> str:
    if status not in ALLOWED:
        raise SystemExit(f"error: status must be one of {sorted(ALLOWED)}, got {status!r}")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        match = ROW.match(line)
        if not match or match.group(1) != step:
            continue
        cells = UNESCAPED_PIPE.split(line)
        current = cells[STATUS_CELL].strip()
        if current == status:
            return text
        cells[STATUS_CELL] = f" {status} "
        lines[i] = "|".join(cells)
        return "\n".join(lines)
    raise SystemExit(f"error: no board row for {step}")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: board_sync.py <COLLABORATION.md> <step> <status>")
    path, step, status = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    path.write_text(set_status(path.read_text(encoding="utf-8"), step, status), encoding="utf-8")


if __name__ == "__main__":
    main()
