# Spec: B1 Scaffolding

Status: draft (awaiting user approval of the decisions below)
Board row: `COLLABORATION.md` → B1
Design context: `PLAN.md` → Architecture, Layout, Images, Build order step 1. Best practices: `BEST_PRACTICES.md` → Phase 0 and Step 1.

## Goal
A runnable project skeleton: Python project with config and lint/test tooling, a local LLM server (`llm`) and Phoenix running in Docker Compose, a pinned model file, and CI that runs lint and unit tests on every PR. After this step, `curl localhost:8080/v1/chat/completions` returns a completion.

## Substeps
Each substep is one commit and one testable behaviour. Tick a box only when its done-check passes.

- [ ] **1. Project tooling.** Files: `pyproject.toml` (Python 3.11, `src/rag_agent/` package, ruff, mypy, pytest settings), `src/rag_agent/__init__.py`, `tests/test_smoke.py` (one placeholder test). Done-check: `uv run ruff check .`, `uv run mypy src`, and `uv run pytest` all pass.
- [ ] **2. Config.** Files: `src/rag_agent/config.py` (pydantic-settings; reads `config.yaml` for tunables and env vars for secrets and environment-specific values; fails fast when a required value is missing), `config.yaml` (placeholder tunables only), `.env.example` (every key, no values). Done-check: unit test loads the config; a unit test shows a missing required value raises at startup.
- [ ] **3. Pre-commit.** Files: `.pre-commit-config.yaml` with ruff, mypy and gitleaks. Done-check: `uv run pre-commit run --all-files` passes on the repo.
- [ ] **4. Model export.** Files: `scripts/export_model.sh`. Copies the Ollama GGUF blob (found with `ollama show --modelfile qwen…` → `FROM` line) to `models/qwen2.5-0.5b-instruct-q4_k_m.gguf`. Done-check: script runs; `sha256sum` of the copy matches the Ollama blob's hash.
- [ ] **5. LLM image.** Files: `docker/llm.Dockerfile` (`FROM` a pinned llama.cpp server tag, `COPY` the GGUF into `/models`, `CMD` with `-c 4096 --jinja`). Done-check: `docker build -f docker/llm.Dockerfile .` succeeds.
- [ ] **6. Compose.** Files: `docker-compose.yml` with services `llm` and `phoenix` (pinned tag, healthcheck, `mem_limit` from PLAN "Memory budget", named volume `phoenix_data`). Done-check: `docker compose up -d` then `docker compose ps` shows both healthy.
- [ ] **7. Smoke test.** Done-check: `curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"local","messages":[{"role":"user","content":"Say hi"}]}'` returns a JSON completion. Record the response in the handoff.
- [ ] **8. CI.** Files: `.github/workflows/ci.yml`. Runs ruff, mypy and pytest on every pull request and on push to `Dev`. Done-check: the workflow passes on the B1 pull request.

## Out of scope
- Layered backend (routes, services, repositories), `/api/v1` routes, and `/health` and `/ready` endpoints (B6).
- Compose split into dev, stage and prod files (B6 or later).
- `make bootstrap` and a Makefile (later, once services exist).
- Ingestion, retrieval and the agent graph (B2 to B4).
- Web tooling (B10), Docker Hub pushes and deploys (B13).

## Decisions needing approval
- [ ] **D1. Dependency manager.** Recommended: `uv` with a lockfile. Alternative: `pip` with `requirements.txt` and a venv.
- [ ] **D2. llama.cpp image tag.** Recommended: the newest stable server tag at build time, pinned by version and recorded in the handoff. Never `latest`. Alternative: a tag you pick now.
- [ ] **D3. Phoenix image tag.** Recommended: the newest release tag at build time, pinned and recorded. Alternative: a tag you pick now.
- [ ] **D4. Package layout.** Recommended: `src/rag_agent/` as in PLAN "Layout". Alternative: flat `rag_agent/` at the repo root.
- [ ] **D5. CPU torch in B1.** Recommended: add it in B2, when embeddings first need it, so B1 stays small. Alternative: add it now with the CPU index.

## Prerequisites (user)
- Install the Docker Compose plugin (`sudo apt install docker-compose-plugin`), as PLAN "Prerequisites" says. The dev PC has Docker 28.3 without it.
- Install `uv` and `pre-commit` on the dev PC, or let the builder add them to the project and document the install line.
- Confirm Ollama still has the Qwen model (`ollama list`). Substep 4 needs it.

## Done when
- All eight substeps are ticked, and each done-check result is in the handoff.
- CI is green on the B1 pull request.
- `.gitignore` still excludes `models/`, and no `.env` or model file is committed.
- Handoff note in `COLLABORATION.md` lists files touched, commands run, the pinned image tags, and the smoke-test output.

## Change log
- 2026-10-18: Draft created from PLAN build order step 1 and BEST_PRACTICES Step 1.
