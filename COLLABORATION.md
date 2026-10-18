# Collaboration and status (read first, every session)

Three roles, each with its own worktree:
- **Claude Code** (id `claude-code`) is the **builder**. It implements every build step.
- **Zed agent** (id `zed`) is the **reviewer**. It reviews PRs and makes small fixes only.
- **The user** (`user`) merges PRs, answers open questions, creates release tags, and approves anything public (Docker Hub pushes, deploys). The user also commits quiz files and works with the **tutor** agent.

`CLAUDE.md` holds the working rules for every agent. This file holds the process, the board and the handoffs.

## Worktrees

Each agent has its own worktree, so neither one edits the other's files. The user keeps the main checkout on `Dev`.

```
PrudcutionLevelAiSytem/   main checkout, branch Dev (user merges and runs /quiz here)
../rag-claude/            builder worktree (Claude Code)
../rag-zed/               reviewer worktree (Zed)
```

Set up once:
```
cd PrudcutionLevelAiSytem
git worktree add --detach ../rag-claude origin/Dev
git worktree add --detach ../rag-zed origin/Dev
cp -r models ../rag-claude/ && cp -r models ../rag-zed/   # gitignored, not in worktrees
```
A worktree can't check out `Dev` while the main checkout is on it, so both use `--detach` and create their step branch inside. Each agent starts its session in its own folder.

## Start of every session (both agents)

1. Read this file: the Board, the Status flow and your role's rules.
2. Run `git status --short`, `git branch --show-current` and `git log --oneline -5` in your worktree.
3. Check the board against `gh pr list --state all`. If they disagree, GitHub wins: correct the board.
4. Act only on a step whose status gives you the turn. Anything modified that you didn't do and that no handoff explains belongs to someone else. Don't revert it; ask the user.

## Status and review

Hand-set statuses:

| Status | Set by | Meaning |
|---|---|---|
| `todo` | — | Not started |
| `doing` | Builder | Building on the step branch |
| `blocked` | Anyone | Stuck. Reason in Notes. The user decides. |
| `done` | User, after the merge | Merged into `Dev`, branch deleted |

Derived from GitHub, not typed into the board:

| Derived state | Source | Whose turn |
|---|---|---|
| `review` | PR open and not merged | The reviewer in the Reviewer column |
| `changes-requested` | PR review decision is "changes requested" | Builder |
| `approved` | PR review decision is "approved" | User merges |

Rules:
- Only one step is `doing` or in review at a time. A new step starts after the previous one is `done`, unless the user says otherwise.
- **Reviewer** is set when the PR opens: `zed`, `user`, or `claude-code`. The reviewer is never the builder. The user may review any step.
- After a `changes-requested`, the builder pushes fixes to the same PR. The PR goes back to open, so it's `review` again.
- Check PR state with `gh pr view <n> --json state,reviewDecision`.

## Claude Code (builder) rules

- Before coding: `git fetch`, cut `bN-<short-name>` from `origin/Dev`, set the step to `doing` with today's date.
- Commit in small commits prefixed `BN: ...`, with the Co-Authored-By trailer. Push the step branch after each commit.
- Follow the matching entries in `BEST_PRACTICES.md`. Use `ctx7` for library docs, as `CLAUDE.md` describes.
- After code changes, run `graphify update .`.
- Before handing to review: run the step's verification check and the test suite. Open a PR into `Dev` with: board step, files touched, commands run and results, anything left out on purpose. Set the Reviewer column and add a handoff note.
- On `changes-requested`: `git pull` on the step branch first (Zed may have pushed small fixes). Read every finding, fix, reply to each on the PR, push.

## Zed (reviewer) rules

- Review only a step whose PR is open. In your worktree: `git fetch && git checkout bN-... && git pull`.
- Check each item and post the result on the PR (`gh pr review` or `gh pr comment`):
  - [ ] The step's verification check and tests pass when re-run.
  - [ ] It does what `PLAN.md` says for this step. Deviations are in the Decisions log.
  - [ ] It follows the matching entries in `BEST_PRACTICES.md`.
  - [ ] No secrets, keys or `.env` content committed. No model files or indexes committed.
  - [ ] Errors are handled. No silent `except: pass`. Network calls have timeouts.
  - [ ] New logic has unit tests. Names and docstrings are clear.
  - [ ] Config values live in `config.yaml` or env, not hard-coded.
- **Small changes you may make yourself:** typos, naming, docstrings, missing or weak tests, formatting, obvious one-line bugs. Limits: under ~20 changed lines in total, no new files, no new dependencies, no change to design, interfaces or config schema. Commit as `BN review: ...` and push to the step branch.
- Anything bigger is a **finding** on the PR, with file, line and a suggested fix.
- End with `approve` or `request changes`. Add a handoff note.
- Never change the plan or design during review. Raise a finding instead.

## After the merge (user)

1. Merge the PR (squash). Delete the step branch.
2. Set the step to `done` on the board.
3. Run `/quiz BN` in the main checkout. The tutor writes the quiz files.
4. Commit the quiz files to `Dev` yourself, then add `quiz: ready` to the step's Notes.
5. Start a tutor session with `claude --agent tutor` when you want to answer the quiz.

## Git workflow

- `Dev` is the integration branch. Each build step gets `bN-<short-name>` (e.g. `b2-ingestion`).
- **Enforcement:** the repo is private on a free GitHub plan, so branch protection and rulesets are not enforced. Agents follow the rules here and in `CLAUDE.md`. The user merges by hand.
- **Auto-merge** (`gh pr merge --auto --squash`) becomes possible once the repo is on GitHub Pro or public, B1 is merged, and `Dev` requires the `ci.yml` check.
- **Failing CI:** the builder fixes it on the same branch. After 2 failed attempts, set `blocked` and ask the user.
- **Release tags:** only the user creates `vX.Y.Z` tags, on `Dev` after a merge.
- **Never (both agents):** push to `Dev`, force-push, merge a PR, create tags, delete files or rewrite history unless the user asks in that conversation. Docker Hub pushes and deploys (B13) need the user's OK even when CI passes.

## Changing the plan

- No silent design changes. A deviation goes in the Decisions log of `PLAN.md` (date, what, why, who). If it changes scope, also add it to the open questions below.

## Board

| Step | Task | Status | Builder | Reviewer | PR | Notes |
|---|---|---|---|---|---|---|
| B1 | Scaffolding: pyproject, config, pre-commit, `scripts/export_model.sh`, `llm` image + Phoenix in compose, `ci.yml` with lint and unit tests | todo | — | — | — | |
| B2 | Ingestion + Chroma + BM25, `rag ingest data/raw` | todo | — | — | — | |
| B3 | Hybrid retrieval, RRF, reranker, unit tests | todo | — | — | — | |
| B4 | LangGraph agent + guardrails, `rag ask`. Includes the `pipeline: vanilla \| agent` flag. | todo | — | — | — | |
| B5 | Phoenix tracing | todo | — | — | — | |
| B6 | FastAPI (`/health`, `/ready`, `/query`) + `api` image, `docker compose up` | todo | — | — | — | |
| B7 | Eval: `rag eval` (Ragas), `rag eval-gate`, eval job in `ci.yml` | todo | — | — | — | |
| B8 | Postgres + Alembic + auth | todo | — | — | — | |
| B9 | Redis: async ingest worker, query cache, per-user budget, conversation memory | todo | — | — | — | |
| B10 | Streaming `/query/stream` + Next.js frontend + `web` image | todo | — | — | — | |
| B11 | Nginx gateway image, rate limits, Cloudflare Tunnel | todo | — | — | — | |
| B12 | Observability: Prometheus, JSON logs, Grafana, k6 load test | todo | — | — | — | |
| B13 | VM + CD: cloud-init, runner, `release.yml`, `deploy.yml` | todo | — | — | — | Needs user confirmation before the first Docker Hub push |
| B14 | README with architecture and trade-offs | todo | — | — | — | |
| B15 | Final phase: production scenarios S1–S16 (see its section in `PLAN.md`) | todo | — | — | — | Starts only after B14 |
| H1 | Uncommitted state: `snap7_client.py` and `.cursor/rules/graphify.mdc` deleted, `requirements.txt` modified | open (user) | — | — | — | Neither agent touches these until the user decides |
| H2 | `BEST_PRACTICES.md` in the repo | done | — | — | — | Committed with this change |
| H3 | Tutor mode scope | done | — | — | — | Decided: every build step gets a quiz after its merge |

## Handoff notes

- _(none yet)_

## Decisions log

- 2026-10-18: Fixed roles: Claude Code builds, Zed reviews and makes small fixes, the user merges and learns.
- 2026-10-18: One worktree per agent. The main checkout stays on `Dev` for the user.
- 2026-10-18: Review state is derived from GitHub PR state, not typed. The reviewer is never the builder.
- 2026-10-18: Zed reads `CLAUDE.md` by default. No `AGENTS.md` is added, because Zed would read it instead.
- 2026-10-18: Tutoring is a separate `tutor` agent. Quizzes are per step, grouped by phase, created with `/quiz BN` after each merge.
- 2026-10-18: Only the user creates release tags, on `Dev`.

## Open questions for the user

- H1: what to do with `snap7_client.py`, the `.cursor/rules/graphify.mdc` deletion and `requirements.txt` (keep, restore or commit).
