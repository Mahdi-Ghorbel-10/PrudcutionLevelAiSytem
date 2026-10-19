# Collaboration and status (read first, every session)

Four roles, each in its own worktree or session:
- **Orchestrator** (Claude Code in the `main/` checkout). It plans and coordinates: it drafts specs for the user to approve, keeps the board in line with GitHub, reads handoffs and reviews, and tells the user what's next. It doesn't write code in `rag-claude/` or `rag-zed/`, and it doesn't push to `Dev` without the user's OK.
- **Claude Code** (id `claude-code`) is the **builder**, in `rag-claude/`. It implements each build step from its spec on `origin/Dev`.
- **Zed agent** (id `zed`) is the **reviewer**, in `rag-zed/`. It reviews PRs and makes small fixes only, against the spec on `origin/Dev`.
- **The user** (`user`) approves specs, merges PRs, creates release tags, and approves anything public (Docker Hub pushes, deploys). The user also commits quiz files, and works with the **tutor** agent, which creates and grades the quizzes.

`CLAUDE.md` holds the working rules for every agent. This file holds the process, the board and the handoffs.

## Principles

- **Spec before code.** Each step has an approved spec in `specs/`. Design choices are settled there, before any code is written.
- **Small, checkable steps.** A substep is one commit with one done-check. Nothing is marked done without its check run.
- **The builder does not grade its own work.** Review is done by a different agent or by the user.
- **State lives in files, not chat.** The board, specs and handoffs are the record. A new session starts from them.
- **Keep always-loaded docs short.** `CLAUDE.md` and this file load every session. Detail goes in the spec or the plan.

## Worktrees

Each agent has its own worktree, so neither one edits the other's files. The user keeps the main checkout on `Dev`, and the orchestrator works from there.

```
rag-workspace/
├── main/          main checkout, branch Dev (user merges and runs /quiz here)
├── rag-claude/    builder worktree (Claude Code)
└── rag-zed/       reviewer worktree (Zed)
```

Set up once:
```
cd rag-workspace/main
git worktree add --detach ../rag-claude origin/Dev
git worktree add --detach ../rag-zed origin/Dev
cp -r models ../rag-claude/ && cp -r models ../rag-zed/   # gitignored, not in worktrees
```
A worktree can't check out `Dev` while the main checkout is on it, so both use `--detach` and create their step branch inside. Each agent starts its session in its own folder.

## Start of every session (both agents)

1. Fetch and read the process files from `Dev`: `git fetch origin`, then `git show origin/Dev:COLLABORATION.md` and `git show origin/Dev:PLAN.md`. Read the Board, the Status flow and your role's rules there. For a step, read its spec with `git show origin/Dev:specs/BN-<name>.md` and nothing else from the specs folder. Don't rely on the copy in your worktree; it can be behind `Dev`.
2. Run `git status --short`, `git branch --show-current` and `git log --oneline -5` in your worktree. If the step branch has `handoffs/BN.md`, read it.
3. Check the board against `gh pr list --state all`. If they disagree, GitHub wins: correct the board.
4. Act only on a step whose status gives you the turn. Anything modified that you didn't do and that no handoff explains belongs to someone else. Don't revert it; ask the user.

## Specs (one file per step)

- Each step has one spec: `specs/Bx-<name>.md`, copied from `specs/_template.md`. The board's Notes column links to it.
- Specs live on `Dev`. The orchestrator drafts them in the `main/` checkout, and the builder and reviewer read them from `origin/Dev`. A spec reaches `Dev` when the user approves it and the orchestrator commits it, with the user's OK.
- Spec status moves `draft` → `approved` → `building` → `review` → `done`. The builder writes no code until the spec is `approved`.
- The user approves a spec by ticking its **Decisions needing approval**. Anything not in the decisions list can be settled by the builder, as long as it fits the spec.
- Each substep is one commit. Tick its box only when its done-check passes, and put the result in the handoff.
- To change a spec after approval, the orchestrator edits it on `Dev` with the user's OK and adds a Change log line. The builder asks for a change in its handoff, not by editing the spec. Design-level changes go in the Decisions log of `PLAN.md` too.
- The reviewer checks the code against the spec's substeps and "Done when". The tutor uses the spec and the merged code for the quiz.

## Status and review

Hand-set statuses:

| Status | Set by | Meaning |
|---|---|---|
| `todo` | — | Not started |
| `spec` | User, by hand (`workflow_dispatch` with status `spec`) | Spec drafted, waiting for the user's approval |
| `doing` | GitHub Actions (`board-sync.yml`), when the step branch is pushed | The spec on that branch says `approved` or `building` |
| `review` | GitHub Actions, when the PR opens, is marked ready, or gets new commits | The PR is open. Reviewer comes from the PR label. |
| `merged` | GitHub Actions, when the PR merges | Merged into `Dev`, branch deleted. |
| `blocked` | User, by hand (`workflow_dispatch` with status `blocked`) | Stuck. Reason in Notes. The user decides. |

The workflow runs `scripts/board_sync.py`, which holds these rules. It only changes the cells it names, and it commits the change to `Dev` as the `github-actions[bot]` user.

Review results are written to Notes by the workflow, so the board shows whose turn it is:

| Notes value | Set when | Whose turn |
|---|---|---|
| `approved` | A review is submitted as approved | User merges |
| `changes requested` | A review asks for changes | Builder |
| (empty) | The builder pushes new commits to the PR | Reviewer |

Rules:
- Only one step is `doing` or in review at a time. A new step starts after the previous one is `merged`, unless the user says otherwise.
- **Reviewer** comes from a PR label: `reviewer:zed` or `reviewer:user`. With no label it is `zed`. Add or change the label at any time, and the board follows. The reviewer is never the builder. The user may review any step.
- After a `changes-requested`, the builder pushes fixes to the same PR. The PR goes back to open, so it's `review` again.
- Check PR state with `gh pr view <n> --json state,reviewDecision`.

## Claude Code (builder) rules

- Before the spec: draft `specs/Bx-<name>.md` from the template, then ask the user to set the step to `spec`. Wait for approval.
- Before coding: the spec is `approved`. `git fetch`, cut `bN-<short-name>` from `origin/Dev`, and push the branch. The workflow sets the step to `doing` when the spec on the branch says `approved`.
- Build substep by substep. One commit per substep, prefixed `BN: ...`, with the Co-Authored-By trailer. Tick the substep's box in the spec and push the step branch after each commit.
- Follow the matching entries in `BEST_PRACTICES.md`. Use `ctx7` for library docs, as `CLAUDE.md` describes.
- After code changes, run `graphify update .`.
- Before handing to review: run the step's verification check and the test suite. Open a PR into `Dev` with: board step, files touched, commands run and results, anything left out on purpose. Write `handoffs/BN.md` on the step branch (format below) and commit it with the PR. The PR opening sets the board to `review`, so don't edit the board yourself.
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
- End with `approve` or `request changes`. Add a `## Review` section to `handoffs/BN.md` on the step branch, with the checklist result.
- Never change the plan or design during review. Raise a finding instead.

## After the merge (user)

1. Merge the PR (squash). Delete the step branch.
2. The workflow sets the step to `merged` and pushes it to `Dev`. Check that it ran (`gh run list --workflow=board-sync.yml`). If it didn't, run it by hand from the Actions tab with the step ID and `status=merged`.
3. Start the tutor (`claude --agent tutor`) and ask it for the quiz for BN. The tutor writes the quiz files. The orchestrator reminds you to do this after each merge. Don't set `quiz_ready` yourself.
4. Commit the quiz files to `Dev`. The workflow sets `quiz_ready` to `true` when they land.
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

| Step | Task | Status | Builder | Reviewer | PR | quiz_ready | Notes |
|---|---|---|---|---|---|---|---|
| B1 | Scaffolding: pyproject, config, pre-commit, `scripts/export_model.sh`, `llm` image + Phoenix in compose, `ci.yml` with lint and unit tests | merged | claude-code | zed | #1 | true | Spec: `specs/B1-scaffolding.md` (approved 2026-10-18). CI green on PR #1. |
| B2 | Ingestion + Chroma + BM25, `rag ingest data/raw` | spec | — | — | — | false | Spec approved 2026-10-19 (D1 to D7). Builder: push b2-ingestion to start, which sets doing. |
| B3 | Hybrid retrieval, RRF, reranker, unit tests | todo | — | — | — | false |  |
| B4 | LangGraph agent + guardrails, `rag ask`. Includes the `pipeline: vanilla \| agent` flag. | todo | — | — | — | false |  |
| B5 | Phoenix tracing | todo | — | — | — | false |  |
| B6 | FastAPI (`/health`, `/ready`, `/query`) + `api` image, `docker compose up` | todo | — | — | — | false |  |
| B7 | Eval: `rag eval` (Ragas), `rag eval-gate`, eval job in `ci.yml` | todo | — | — | — | false |  |
| B8 | Postgres + Alembic + auth | todo | — | — | — | false |  |
| B9 | Redis: async ingest worker, query cache, per-user budget, conversation memory | todo | — | — | — | false |  |
| B10 | Streaming `/query/stream` + Next.js frontend + `web` image | todo | — | — | — | false |  |
| B11 | Nginx gateway image, rate limits, Cloudflare Tunnel | todo | — | — | — | false |  |
| B12 | Observability: Prometheus, JSON logs, Grafana, k6 load test | todo | — | — | — | false |  |
| B13 | VM + CD: cloud-init, runner, `release.yml`, `deploy.yml` | todo | — | — | — | false | Needs user confirmation before the first Docker Hub push |
| B14 | README with architecture and trade-offs | todo | — | — | — | false |  |
| B15 | Final phase: production scenarios S1–S16 (see its section in `PLAN.md`) | todo | — | — | — | false | Starts only after B14 |
| H1 | Uncommitted state: `snap7_client.py` and `.cursor/rules/graphify.mdc` deleted, `requirements.txt` emptied | resolved | — | — | — | — | Deletions and the empty `requirements.txt` are committed in `56d8b68`. The user decided these files are not needed. |
| H2 | `BEST_PRACTICES.md` in the repo | resolved | — | — | — | — | Committed with this change |
| H3 | Tutor mode scope | resolved | — | — | — | — | Decided: every build step gets a quiz after its merge |

## Handoff notes

One file per step: `handoffs/BN.md`, written by the builder on the step branch and reviewed by Zed in a `## Review` section of the same file. The PR brings it into `Dev`. Sections: files touched, commands run and results, deviations, next step. The B1 handoff is in `handoffs/B1.md`.

## Decisions log

- 2026-10-18: Fixed roles: Claude Code builds, Zed reviews and makes small fixes, the user merges and learns.
- 2026-10-18: One worktree per agent. The main checkout stays on `Dev` for the user.
- 2026-10-18: Review state is derived from GitHub PR state, not typed. The reviewer is never the builder.
- 2026-10-18: Zed reads `CLAUDE.md` by default. No `AGENTS.md` is added, because Zed would read it instead.
- 2026-10-18: Tutoring is a separate `tutor` agent. Quizzes are per step, grouped by phase, created with `/quiz BN` after each merge.
- 2026-10-18: Only the user creates release tags, on `Dev`.
- 2026-10-18: Board statuses are `todo`, `spec`, `doing`, `review`, `merged`, `blocked`. `review` is derived from the PR. `quiz_ready` is a separate column, set to `true` by `/quiz`.
- 2026-10-18: Spec-driven steps. One spec per step in `specs/`. The builder codes only from an approved spec. One commit per substep. Tutor reads the spec, not the plan.
- 2026-10-19: Four roles. The orchestrator (Claude Code in `main/`) plans and coordinates, and does not push to `Dev` without the user's OK. The builder (`rag-claude/`) and the reviewer (`rag-zed/`) read specs from `origin/Dev`. The tutor agent creates and grades the quizzes, when the user starts it after a merge.
- 2026-10-19: The board is updated by `board-sync.yml` from GitHub events (rules in `scripts/board_sync.py`). `doing`, `review`, `merged` and `quiz_ready` are automatic. `spec` and `blocked` are set by hand with `workflow_dispatch`. The Reviewer comes from a `reviewer:` label, default `zed`. Review results go to Notes.
- 2026-10-19: Agents read `COLLABORATION.md` and `PLAN.md` from `Dev`, not from their worktree copy. Each step's handoff is `handoffs/BN.md` on its step branch, merged with the PR. No shared handoff section.

## Open questions for the user

- None. H1 is resolved.
