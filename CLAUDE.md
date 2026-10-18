## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- For library, framework, SDK, API, CLI or cloud-service docs (syntax, config, version migration, setup), use the `ctx7` CLI instead of training data or web search:
  1. `npx ctx7@latest library <name> "<what to look up>"` with the official name (e.g. "Next.js", "Customer.io"). Pick the best match (`/org/project`).
  2. `npx ctx7@latest docs <libraryId> "<what to look up>"`, one concept per query.
  Max 3 commands per question. Don't include secrets in queries. On a quota error, tell the user and suggest `npx ctx7@latest login` or `CONTEXT7_API_KEY`. Don't use it for refactoring, business logic, code review or general concepts.

## Collaboration (Claude Code and the Zed agent)

Claude Code is the builder, Zed is the reviewer, and the user merges. Each agent works in its own git worktree. The full protocol, roles, status flow and board are in `COLLABORATION.md`. Read it before starting work.

Rules for every agent:
- Read `COLLABORATION.md` and run `git status` in your worktree before editing anything.
- Build a step only from its approved spec in `specs/`. One commit per substep. Claim a build step (status `doing`) on the board before editing its files. Don't edit files of a step another agent is reviewing or building.
- Never revert or delete changes you didn't make. Files marked `open` on the board belong to the user.
- Finish with a board update and a handoff note in `COLLABORATION.md`, listing files touched, commands run and results, and the next step.
- Record any deviation from the plan in the Decisions log of `PLAN.md`. Don't change the design silently.
- Commit and push on your own step branch. Never push to `Dev`, force-push, or merge a PR; the user merges.
- Don't delete files or rewrite history unless the user asks in that conversation.
- Tutor quizzes are created with `/quiz BN` after a merge. Only the `tutor` agent reads `quizzes/answers/`, and only to grade. Every other agent leaves that folder alone.
- After code changes, run `graphify update .`.