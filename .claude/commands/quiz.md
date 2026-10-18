---
description: Generate the tutor quiz for a merged build step
argument-hint: <step id, e.g. B2>
---

Create the quiz for build step $ARGUMENTS. The step must already be merged into `Dev`.

1. Confirm the step is merged. Find its branch and merge commit with `git log --oneline --all --grep="$ARGUMENTS"`. If it is not merged, stop and tell the user.
2. Look up the step's phase in `COLLABORATION.md` → Board, using the phase grouping from `PLAN.md`:
   - Phase 1 = B1–B5, Phase 2 = B6–B7, Phase 3 = B8–B11, Phase 4 = B12–B14, Phase 5 = B15.
3. Start the `tutor` agent to read the merged code and write the two quiz files described in `.claude/agents/tutor.md`:
   - `quizzes/phase-N/$ARGUMENTS-<name>.md`
   - `quizzes/answers/phase-N/$ARGUMENTS-<name>.key.md`
4. Put the quiz in the working tree. Do not commit it, because the user commits quiz files to `Dev`.
5. Add `quiz: ready` to the step's Notes on the board in `COLLABORATION.md`.
6. Reply with the two file paths and the number of questions. Do not show the answers.
