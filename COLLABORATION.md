# Collaboration and status (read first, every session)

Three roles, each with its own worktree:
- **Claude Code** (id `claude-code`) is the **builder**. It implements every build step.
- **Zed agent** (id `zed`) is the **reviewer**. It reviews PRs and makes small fixes only.
- **The user** (`user`) merges PRs, answers open questions, creates release tags, and approves anything public (Docker Hub pushes, deploys). The user also commits quiz files and works with the **tutor** agent.

`CLAUDE.md` holds the working rules for every agent. This file holds the process, the board and the handoffs.

## Principles

- **Spec before code.** Each step has an approved spec in `specs/`. Design choices are settled there, before any code is written.
- **Small, checkable steps.** A substep is one commit with one done-check. Nothing is marked done without its check run.
- **The builder does not grade its own work.** Review is done by a different agent or by the user.
- **State lives in files, not chat.** The board, specs and handoffs are the record. A new session starts from them.
- **Keep always-loaded docs short.** `CLAUDE.md` and this file load every session. Detail goes in the spec or the plan.

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

1. Read this file: the Board, the Status flow and your role's rules. For a step, read its spec in `specs/` and nothing else from the specs folder.
2. Run `git status --short`, `git branch --show-current` and `git log --oneline -5` in your worktree.
3. Check the board against `gh pr list --state all`. If they disagree, GitHub wins: correct the board.
4. Act only on a step whose status gives you the turn. Anything modified that you didn't do and that no handoff explains belongs to someone else. Don't revert it; ask the user.

## Specs (one file per step)

- Each step has one spec: `specs/Bx-<name>.md`, copied from `specs/_template.md`. The board's Notes column links to it.
- Spec status moves `draft` → `approved` → `building` → `review` → `done`. The builder writes no code until the spec is `approved`.
- The user approves a spec by ticking its **Decisions needing approval**. Anything not in the decisions list can be settled by the builder, as long as it fits the spec.
- Each substep is one commit. Tick its box only when its done-check passes, and put the result in the handoff.
- To change a spec after approval, the builder edits the spec first and adds a Change log line. Design-level changes need the user's OK, and go in the Decisions log of `PLAN.md` too.
- The reviewer checks the code against the spec's substeps and "Done when". The tutor uses the spec and the merged code for the quiz.

## Status and review

Hand-set statuses:

| Status | Set by | Meaning |
|---|---|---|
| `todo` | — | Not started |
| `spec` | Builder | Spec drafted, waiting for the user's approval |
| `doing` | Builder | Building on the step branch, after the spec is approved |
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

- Before the spec: draft `specs/Bx-<name>.md` from the template and set the step to `spec`. Wait for approval.
- Before coding: the spec is `approved`. `git fetch`, cut `bN-<short-name>` from `origin/Dev`, set the step to `doing` with today's date.
- Build substep by substep. One commit per substep, prefixed `BN: ...`, with the Co-Authored-By trailer. Tick the substep's box in the spec and push the step branch after each commit.
- Follow the matching entries in `BEST_PRACTICES.md`. Use `ctx7` for library docs, as `CLAUDE.md` describes.
- After code changes, run `graphify update .`.
- Before handing to review: run the step's verification check and the test suite. Open a PR into `Dev` with: board step, files touched, commands run and results, anything left out on purpose. Set the Reviewer column and add a handoff note.
- On `changes-requested`: `git pull` on the step branch first (Zed may have pushed small fixes). Read every finding, fix, reply to each on the PR, push.

## Zed (reviewer) rules

- Review only a step whose PR is open. In your worktree: `git fetch && git checkout bN-... && git pull`.
- Check each item and post the result on the PR (`gh pr review` or `gh pr comment`):
  - [ ] The step's verification check and tests pass when re-run.
  - [ ] Every substep in the spec is ticked, and its done-check result is in the handoff.
  - [ ] It does what the spec says. The spec matches `PLAN.md`; deviations are in the Decisions log.
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
| B1 | Scaffolding: pyproject, config, pre-commit, `scripts/export_model.sh`, `llm` image + Phoenix in compose, `ci.yml` with lint and unit tests | review | claude-code | zed | #1 | Spec: `specs/B1-scaffolding.md` (approved 2026-10-18). CI green on PR #1. |
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
| H1 | Uncommitted state: `snap7_client.py` and `.cursor/rules/graphify.mdc` deleted, `requirements.txt` emptied | done | — | — | — | Deletions and the empty `requirements.txt` are committed in `56d8b68`. The user decided these files are not needed. |
| H2 | `BEST_PRACTICES.md` in the repo | done | — | — | — | Committed with this change |
| H3 | Tutor mode scope | done | — | — | — | Decided: every build step gets a quiz after its merge |

## Handoff notes

- **B1, builder (claude-code) → reviewer (zed), 2026-10-18.** PR #1 into `Dev`, branch `b1-scaffolding`, worktree `../rag-claude`.
  - Files: `pyproject.toml`, `uv.lock`, `src/rag_agent/`, `tests/`, `config.yaml`, `.env.example`, `.pre-commit-config.yaml`, `scripts/export_model.sh`, `docker/llm.Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.github/workflows/ci.yml`, `specs/B1-scaffolding.md`, this board.
  - Pinned: llama.cpp `ghcr.io/ggml-org/llama.cpp:server-b11718`, Phoenix `arizephoenix/phoenix:20.23.0`.
  - Checks run: ruff check and format, mypy, pytest (5 passed), pre-commit on all files, model copy checksum matches the Ollama blob, `docker compose` healthy for `llm` and `phoenix`, smoke test returned a completion on `localhost:8081`, CI green on PR #1.
  - Deviations, all recorded in the spec change log: llm host port 8081 (Jenkins holds 8080), `--host 0.0.0.0 --port 8080` in the CMD, gitleaks as a local hook (Go is not installed), CI action pinned to `setup-uv@v7` after `v10` failed to resolve.
  - Next for zed: review against the spec checklist. Small fixes only. Anything bigger is a finding on the PR.
  - Note for the user: the `llm` and `phoenix` containers are still running on this PC (`docker compose down` stops them).

## Decisions log

- 2026-10-18: Fixed roles: Claude Code builds, Zed reviews and makes small fixes, the user merges and learns.
- 2026-10-18: One worktree per agent. The main checkout stays on `Dev` for the user.
- 2026-10-18: Review state is derived from GitHub PR state, not typed. The reviewer is never the builder.
- 2026-10-18: Zed reads `CLAUDE.md` by default. No `AGENTS.md` is added, because Zed would read it instead.
- 2026-10-18: Tutoring is a separate `tutor` agent. Quizzes are per step, grouped by phase, created with `/quiz BN` after each merge.
- 2026-10-18: Only the user creates release tags, on `Dev`.
- 2026-10-18: Spec-driven steps. One spec per step in `specs/`. The builder codes only from an approved spec. One commit per substep. Tutor reads the spec, not the plan.

## Open questions for the user

- None. H1 is resolved.
