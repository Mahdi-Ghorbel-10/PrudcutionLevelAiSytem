#!/usr/bin/env bash
# Bring this worktree up to date with origin/Dev at the start of an agent session.
#
# Usage: sync_worktree.sh <orchestrator|builder|reviewer> [--dry-run]
#
# Runs as a SessionStart hook (see .claude/settings.local.json in each worktree).
# It never commits or pushes. It skips a worktree with uncommitted changes, and it
# aborts a merge that conflicts. It prints one line, which the agent sees as context.
# It always exits 0, so it can't block a session.
set -uo pipefail

role="${1:?usage: sync_worktree.sh <orchestrator|builder|reviewer> [--dry-run]}"
dry_run="${2:-}"
dir="${CLAUDE_PROJECT_DIR:-$PWD}"

g() { git -C "$dir" "$@"; }
say() { echo "sync: $*"; }

if ! g rev-parse --git-dir >/dev/null 2>&1; then
  say "not a git worktree, nothing done"
  exit 0
fi

if ! g fetch --quiet origin 2>/dev/null; then
  say "fetch failed (offline?), nothing changed"
  exit 0
fi

head_name="$(g symbolic-ref --short -q HEAD || echo DETACHED)"
head="$(g rev-parse HEAD)"
dev="$(g rev-parse origin/Dev)"

if [ -n "$(g status --porcelain --untracked-files=no)" ]; then
  say "$head_name has uncommitted changes, not synced"
  exit 0
fi

if g merge-base --is-ancestor "$dev" "$head"; then
  say "$head_name already includes origin/Dev"
  exit 0
fi

case "$role" in
  orchestrator)
    # The orchestrator's checkout is the source of the process files, so it only reports.
    say "$head_name is $(g rev-list --count HEAD..origin/Dev) commit(s) behind origin/Dev"
    ;;
  reviewer)
    # Move only a checkout that is already on Dev's history. A review in progress sits
    # on a step branch, so it is left alone.
    if g merge-base --is-ancestor "$head" "$dev"; then
      if [ "$dry_run" = "--dry-run" ]; then
        say "would detach at origin/Dev"
      else
        g checkout -q --detach origin/Dev && say "detached at origin/Dev"
      fi
    else
      say "on a step branch, left alone"
    fi
    ;;
  builder)
    if g merge-base --is-ancestor "$head" "$dev"; then
      if [ "$dry_run" = "--dry-run" ]; then
        say "would fast-forward $head_name to origin/Dev"
      else
        g merge -q --ff-only origin/Dev && say "fast-forwarded $head_name to origin/Dev"
      fi
    elif [ "$dry_run" = "--dry-run" ]; then
      say "would merge origin/Dev into $head_name"
    elif g merge -q --no-edit origin/Dev; then
      say "merged origin/Dev into $head_name"
    else
      g merge --abort
      say "merging origin/Dev into $head_name conflicts, merge aborted. Resolve it by hand"
    fi
    ;;
  *)
    say "unknown role '$role', nothing done"
    ;;
esac

exit 0
