# Spec: Bx <name>

Status: draft (`draft` → `approved` → `building` → `review` → `done`)
Board row: `COLLABORATION.md` → Bx
Design context: `PLAN.md` → Architecture, Layout, Images. Best practices: `BEST_PRACTICES.md` → Step x.

## Goal
One or two sentences: what exists after this step that did not exist before.

## Substeps
Each substep is one commit and one testable behaviour. Tick a box only when its done-check passes.

- [ ] **1. <name>.** Files: `...`. Done-check: `<command>` → `<expected result>`.
- [ ] **2. <name>.** Files: `...`. Done-check: `...`.

## Out of scope
What this step must not do, so the builder does not drift into later steps.

## Decisions needing approval
Design-level choices only. Each one lists the recommended option. Builder does not start until these are marked approved.
- [ ] **D1.** Question. Recommended: `...`. Alternative: `...`.

## Prerequisites (user)
Anything only the user can do (install tools, credentials, confirmations).

## Done when
- All substeps ticked, and each done-check was run and its result recorded in the handoff.
- CI is green on the PR.
- Handoff note in `COLLABORATION.md` lists files touched, commands run, and results.

## Change log
- YYYY-MM-DD: what changed in the spec, why, who. Design changes also go in the Decisions log of `PLAN.md`.
