# Plan: Agentic RAG Platform (CPU-first, Dockerized, CI/CD, Docker Hub distributed)

## Collaboration and status (read first, every session)
Two agents work in this repo on the same working tree: **Claude Code** (owner id `claude-code`) and the **Zed agent** (owner id `zed`). This section is the shared source of truth for who is doing what. `CLAUDE.md` holds the working rules; this file holds the state.

**Start of every session**
1. Read this section and the Board below.
2. Run `git status --short` and `git log --oneline -3`. Anything modified that is not on the Board is someone else's work until the user says otherwise. Don't revert it.

**Claiming work**
- Before editing code for a build step, set its Owner to your id and Status to `doing`, with today's date in Notes. Update this file first, then edit code.
- One owner per build step. If a step is `doing` for the other agent, don't edit its files. Write a question under Open questions or ask the user.
- Claims are advisory because we share one working tree. Re-read the Board before each edit if your last read was more than a few minutes ago.
- Finish or hand off one step before starting another.

**Finishing or stopping**
- Set Status to `review` (the other agent or the user should check it) or `done` (tests passed; say which ones in Notes). Set `blocked` with a reason if you are stuck.
- Add a Handoff note under the Board: files touched, commands run and their results, what is left, and what the next owner should do first.
- If you stop midway, say so in the handoff. Never leave a step `doing` without a note.

**Changing the plan**
- Don't change the design silently. A deviation goes in the Decisions log (date, what, why, who). If it changes scope, also add it to Open questions for the user.
- Deleting files and rewriting git history happen only when the user asks for them in that conversation. Committing and pushing follow the Git workflow below.

### Git workflow (automatic)
`Dev` is the integration branch. Each build step gets its own branch, `bN-<short-name>` (e.g. `b2-ingestion`), cut from the latest `Dev`.
- **Commit:** the owning agent commits on its step branch on its own, in small commits prefixed with the step id (`B2: ...`), with the Co-Authored-By trailer.
- **Push:** the owner pushes its step branch after each commit. Only the step branch, never `Dev`.
- **Pull request:** when a step moves to `review`, the owner opens a PR into `Dev`. The PR body lists the board step, files touched and test results.
- **Auto-merge:** the owner enables auto-merge (`gh pr merge --auto --squash`). GitHub merges once the required checks pass. Enable this only after B1 is merged and `Dev` requires the `ci.yml` check. Until then, nothing merges without the user.
- **Failing CI:** fix it on the same branch. After 2 failed attempts, set the step `blocked` and ask the user.
- **Sync:** before starting a step, `git fetch` and rebase onto `Dev`.
- **After merge:** delete the step branch and set the step `done`.
- **Never:** push to `Dev`, force-push, or merge by hand. Docker Hub pushes and deploys (B13) need the user's OK, even when CI passes.

### Board
| Step | Task | Owner | Status | Notes |
|---|---|---|---|---|
| B1 | Scaffolding: pyproject, config, pre-commit, `scripts/export_model.sh`, `llm` image + Phoenix in compose, `ci.yml` with lint and unit tests | — | todo | |
| B2 | Ingestion + Chroma + BM25, `rag ingest data/raw` | — | todo | |
| B3 | Hybrid retrieval, RRF, reranker, unit tests | — | todo | |
| B4 | LangGraph agent + guardrails, `rag ask` | — | todo | |
| B5 | Phoenix tracing | — | todo | |
| B6 | FastAPI (`/health`, `/ready`, `/query`) + `api` image, `docker compose up` | — | todo | |
| B7 | Eval: `rag eval` (Ragas), `rag eval-gate`, eval job in `ci.yml` | — | todo | |
| B8 | Postgres + Alembic + auth | — | todo | |
| B9 | Redis: async ingest worker, query cache, per-user budget, conversation memory | — | todo | |
| B10 | Streaming `/query/stream` + Next.js frontend + `web` image | — | todo | |
| B11 | Nginx gateway image, rate limits, Cloudflare Tunnel | — | todo | |
| B12 | Observability: Prometheus, JSON logs, Grafana, k6 load test | — | todo | |
| B13 | VM + CD: cloud-init, runner, `release.yml`, `deploy.yml` | — | todo | Needs user confirmation before the first Docker Hub push |
| B14 | README with architecture and trade-offs | — | todo | |
| B15 | Final phase: production scenarios S1–S16 (see its section) | — | todo | Starts only after B14 |
| H1 | Uncommitted state: `snap7_client.py` and `.cursor/rules/graphify.mdc` deleted, `requirements.txt` modified, `models/` and `PLAN.md` untracked | user | open | Neither agent touches these until the user decides |
| H2 | `BEST_PRACTICES.md` is referenced in this plan but does not exist | user | open | Create it or remove the reference |

### Handoff notes
- _(none yet)_

### Decisions log
- 2026-10-18: Collaboration protocol adopted (this section and the matching rules in `CLAUDE.md`). Shared working tree; claims are advisory.

### Open questions for the user
- Should `PLAN.md` and `CLAUDE.md` be committed to `Dev`? Recommended: yes, so both agents read the same version.
- Does the Zed agent load `CLAUDE.md` as project rules? Check by asking it to quote the Collaboration section.
- Stay on one shared working tree (current setup, fine while steps run in order) or give each agent its own git worktree for parallel steps?

## Context
Personal learning project: build a RAG system with production-grade tools (OpenAI-compatible model server, LangGraph, hybrid search + RRF, cross-encoder rerank, Phoenix tracing, Ragas evals), **wrapped in a production web stack (Next.js frontend, Nginx gateway, auth, Postgres, Redis queue/cache, Prometheus/Grafana) and shipped through a CI/CD pipeline** that tests, evaluates, scans, builds and pushes images to Docker Hub, then deploys them with `docker compose up`. The repo is empty except graphify tooling (`CLAUDE.md`, `.claude/settings.json`, `.cursor/rules/graphify.mdc`).

Target machine (checked): dev PC, i7-10750H 6c/12t with AVX2, 15 GB RAM (~5.5 GB free in practice), **no NVIDIA GPU visible on PCI** (only Intel UHD), Docker 28.3 **without the compose plugin**, 25 GB free disk.
So we use **CPU inference with llama.cpp `llama-server`**, which has the same OpenAI-compatible API as SGLang/vLLM. The app only knows `LLM_BASE_URL`, so a GPU swap later (llama.cpp CUDA image, or SGLang) is a compose/env change.

**Best practices per phase:** see `BEST_PRACTICES.md` (patterns adapted from reference repos, mapped to this stack). Follow it alongside each build step.

**Learning goals covered:** agent system design (graph state, routing, retry loops, guardrails, memory, evals, tracing) + web system design (gateway, auth, async jobs, caching, rate limiting, streaming, observability) + CI/CD (quality gates, eval gate, image scanning, versioned releases, automated deploy).

## Model choices
| Role | Model | Size / RAM |
|---|---|---|
| Generator / router / rewriter | `Qwen2.5-0.5B-Instruct` **Q4_K_M**, **already downloaded via Ollama** (`hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M`, 491 MB) | ~0.8 GB runtime @ 4k ctx |
| Embeddings | `BAAI/bge-small-en-v1.5` | ~130 MB |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | ~90 MB |
| Ragas judge | `JUDGE_BASE_URL`/`JUDGE_MODEL` env; defaults to the local model (noisy scores, documented) | — |

**Reusing the Ollama download:** Ollama stores it as a raw GGUF blob (`/usr/share/ollama/.ollama/models/blobs/sha256-74a4da8c…`). `scripts/export_model.sh` finds the path with `ollama show --modelfile <name> | grep ^FROM` and copies it to `models/qwen2.5-0.5b-instruct-q4_k_m.gguf` (gitignored, already in the Docker build context). No re-download. If quality is poor later, try Q8_0 (`ollama pull hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q8_0`, then re-export).
**Dev shortcut:** `LLM_BASE_URL=http://localhost:11434/v1` + `LLM_MODEL=hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M` uses the host's Ollama directly while iterating with `uv run`. Containers use `rag-llm` (`http://llm:8080/v1`).

Upgrade path once it works: Qwen3-0.6B (thinking off) → Qwen2.5-1.5B (still fine on this CPU).

## Images (Docker Hub, `${DOCKERHUB_USER}`)
| Image | Base | Contents |
|---|---|---|
| `rag-llm` | `ghcr.io/ggml-org/llama.cpp:server` | GGUF baked into `/models`, so pull-and-run works offline |
| `rag-api` | `python:3.11-slim` + uv, CPU-only torch | app code + embedder + reranker baked into the HF cache. **Also runs the worker** (same image, `command: rag worker`) |
| `rag-web` (new) | `node:22-alpine`, Next.js `output: "standalone"` | chat UI, upload page, built static assets |
| `rag-gateway` (new) | `nginx:1.27-alpine` | `nginx.conf` baked in, so the deploy machine needs no config files |
| Phoenix | `arizephoenix/phoenix` (upstream) | — |
| Postgres (new) | `postgres:16-alpine` (upstream) | users, API keys, sessions, LangGraph checkpoints, ingest jobs, feedback |
| Redis (new) | `redis:7-alpine` (upstream) | job queue, query cache, rate-limit counters |
| Prometheus + Grafana (new) | upstream, configs from the `deploy/` bundle | metrics and dashboards (compose profile `observability`) |

**When each happens:**
- **Now, during development:** nothing of ours comes from Docker Hub. `docker compose build` builds our images locally. Docker only pulls upstream base images automatically. Day-to-day code iteration can also run with `uv run` / `pnpm dev` outside Docker against the `llm`, `phoenix`, `postgres` and `redis` containers.
- **Release (CI, after you confirm the first push manually):** pushing a git tag `vX.Y.Z` makes GitHub Actions build, scan and push `${DOCKERHUB_USER}/rag-*:X.Y.Z`, and attach a `deploy-X.Y.Z.tar.gz` bundle (compose file, `.env.example`, Prometheus/Grafana configs) to a GitHub Release.
- **Later, on any machine:** unpack the deploy bundle, fill `.env`, then `docker compose pull && docker compose up -d`. No source code or build needed.

Model weights are baked in so pull-and-run works without first-run downloads. All images are pinned by version tag, never `latest`. **Secrets are never baked into images**; they come from `.env` (local) or GitHub Actions secrets (CI).
Volumes: `chroma_data`, `phoenix_data`, `pg_data`, `redis_data`, `grafana_data`; bind mount `./data/raw` for documents.

## Architecture

### System
```
Browser ─► Cloudflare Tunnel (HTTPS, public URL) ─► rag-gateway (Nginx)
   ├─ /                 ─► rag-web (Next.js)
   ├─ /api/*            ─► rag-api (FastAPI)            rate limit 20 r/s
   ├─ /api/query/stream ─► rag-api (SSE, buffering off) rate limit 2 r/s
   └─ /api/auth/login   ─► rag-api                      rate limit 5 r/min
rag-api ─► llm (llama-server) · Chroma (embedded, volume) · Postgres · Redis · Phoenix (OTel)
rag-api ─► Redis queue ─► rag-worker (same image) ─► IngestionPipeline ─► Chroma + BM25 rebuild
Prometheus ◄─ /metrics (api, worker, nginx exporter) ─► Grafana
Phoenix, Grafana, Prometheus, /docs, /metrics: bound to 127.0.0.1 only, never through the gateway
```

### Request flow (LangGraph)
```
POST /query or /query/stream  (auth: JWT or API key; X-Request-ID propagated)
 └─► cache lookup (Redis, key = hash(normalized query + corpus_version)) ── hit ─► return cached answer
 └─► LangGraph (checkpointer = Postgres, thread_id = session_id → conversation memory):
      input_guard ─(blocked)─► END
          └─► condense_question (uses chat history → standalone query)
                └─► router (JSON-schema constrained: retrieve|direct)
                      ├─ direct ─► direct_answer ─► END
                      └─ retrieve ─► hybrid_retrieve (Chroma top20 + BM25 top20 → RRF k=60 → top10)
                                    ─► rerank (cross-encoder → top4)
                                    ─► context_guard (strip instruction-like text from chunks)
                                    ─► grade (max rerank score ≥ threshold?)
                                          ├─ no & attempts<2 ─► rewrite_query ─► hybrid_retrieve
                                          └─ yes / exhausted ─► generate (cited, tokens streamed) ─► output_guard ─► END
 └─► cache write · persist turn · return answer + citations + trace_id
Phoenix (OTel via openinference) traces every node, LLM call, retrieval span.
Prometheus counts requests, latency per node, cache hit rate, route taken, retries, guard blocks.
```

## Key design decisions
- Relevance grading uses reranker scores (deterministic, no extra LLM call). The retry loop rewrites the query.
- The router uses llama-server `response_format` JSON schema so a 0.5B model returns valid labels, with `retrieve` as the fallback.
- The sync embedder/reranker run in `asyncio.to_thread`.
- One `IngestionPipeline` class is shared by the CLI and the worker. Content-hash chunk IDs + Chroma `upsert` make re-ingest idempotent. The BM25 index is rebuilt from the Chroma docstore at startup and after ingest (single source of truth).
- Phoenix runs as its own container. The app calls `phoenix.otel.register(project_name=..., endpoint="http://phoenix:6006/v1/traces", auto_instrument=True)`.
- Ragas ≥0.2 (`EvaluationDataset`, `Faithfulness`, `ResponseRelevancy`, `LLMContextPrecisionWithReference`, `LLMContextRecall`). The eval command runs the pipeline over `{question, ground_truth, source_doc}` entries.
- Loaders are pypdf, python-docx, txt/md. CPU torch comes via `[tool.uv.sources]` with the pytorch-cpu index, which keeps the image ~1.5 GB instead of ~5 GB.

### New decisions (web system design)
- **Async ingestion.** `POST /ingest` stores the upload, creates an `ingest_jobs` row and enqueues a job on Redis (arq). It returns `202 {job_id}` immediately; `GET /ingest/{job_id}` reports status. The worker is idempotent (content-hash IDs), retries with backoff up to 3 times, and bumps `corpus_version` when done.
- **Concurrency on one Chroma.** Chroma runs embedded in a shared volume, so only the worker writes. After a job, the worker publishes `corpus_updated` on Redis pub/sub; the API reloads its BM25 index on that event. (Upgrade path: Chroma server mode if this becomes a bottleneck.)
- **Query cache.** Exact-match cache in Redis keyed on normalized query + `corpus_version`, TTL 24 h. Bumping `corpus_version` invalidates everything stale for free. Only cache answers that passed `output_guard`, never `direct` small talk tied to a session.
- **Conversation memory.** LangGraph `AsyncPostgresSaver` checkpointer, `thread_id = session_id`. `condense_question` turns follow-ups ("and the second one?") into standalone queries before routing. History is capped at the last 6 turns to fit 4k context.
- **Auth.** Users + bcrypt passwords in Postgres, short-lived JWT access token + refresh token in an httpOnly cookie for the web app; hashed API keys for CLI/scripts. Roles: `viewer` (query), `editor` (query + ingest), `admin` (users, delete docs).
- **Streaming.** `POST /query/stream` returns SSE events: `route`, `sources`, `token`, `done` (with `trace_id`), `error`. The non-streaming `/query` stays for evals and tests.
- **Rate limiting.** Nginx per-IP limits (above) plus a per-user token budget in Redis inside the API, since IPs are shared behind a tunnel.
- **Feedback loop.** `POST /feedback {trace_id, rating, comment}` stores thumbs up/down in Postgres and annotates the Phoenix trace. A `rag eval export-feedback` command turns downvoted queries into new eval entries.
- **Migrations.** Alembic, run as a one-shot `migrate` compose service that `api` and `worker` depend on (`condition: service_completed_successfully`).
- **Health vs readiness.** `/health` = process alive (cheap, used by Docker). `/ready` = Postgres, Redis, LLM and Chroma reachable (used by the CD smoke test).
- **Structured logs.** JSON logs with `request_id`, `user_id`, `route`, `latency_ms` from Nginx, API and worker, so one request can be followed end to end.
- **Config.** `config.yaml` for tunables, env vars for anything secret or environment-specific, validated at startup with pydantic-settings (fail fast on missing values).

### CI/CD (new)
| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | every PR + push to Dev | ruff, mypy, pytest (unit), web lint + typecheck + build; then integration job: `docker compose -f compose.ci.yml up` (llm + api + postgres + redis), run integration tests and the **eval gate** |
| `release.yml` | git tag `v*` | build images with buildx + GHA layer cache, **Trivy scan** (fail on HIGH/CRITICAL fixable), push to Docker Hub with version tag, attach deploy bundle to a GitHub Release |
| `deploy.yml` | after `release.yml` succeeds (manual approval via a GitHub `production` environment) | on a **self-hosted runner** on the deploy machine: `docker compose pull`, `docker compose up -d`, wait for `/ready`, run smoke queries; on failure, redeploy the previous tag (rollback) |

- **Eval gate, made deterministic.** A 0.5B judge gives noisy Ragas scores, so CI blocks only on **retrieval metrics** that need no LLM judge: hit rate@4 and MRR against `source_doc` labels, plus "router picks `direct` for greetings" and "answer cites at least one source". Thresholds live in `evals/thresholds.yaml`. Full Ragas runs nightly / on demand and are reported as a non-blocking artifact.
- **Pre-commit hooks** (ruff, mypy, prettier, gitleaks) so most CI failures are caught locally.
- **Secrets:** `DOCKERHUB_USER`, `DOCKERHUB_TOKEN` (access token, not password), `JWT_SECRET` in GitHub secrets; deploy machine keeps its own `.env`.
- **Branch protection on Dev:** PR required, CI must pass, no direct pushes or force pushes.

## Layout
```
pyproject.toml / uv.lock     py3.11, CPU torch index
.env.example                 DOCKERHUB_USER, IMAGE_TAG, LLM_BASE_URL, LLM_MODEL, JUDGE_*, PHOENIX_ENDPOINT,
                             DATABASE_URL, REDIS_URL, JWT_SECRET, CORS_ORIGINS
config.yaml                  chunking, top_k values, rrf_k, thresholds, model names, cache TTL, history turns
.pre-commit-config.yaml
.github/workflows/           ci.yml, release.yml, deploy.yml
docker/llm.Dockerfile        FROM llama.cpp:server + ADD GGUF; CMD -m ... -c 4096 -t 6 --jinja
docker/api.Dockerfile        multi-stage uv build; pre-downloads embedder+reranker; non-root user; HEALTHCHECK
docker/web.Dockerfile        multi-stage pnpm build → Next.js standalone; non-root user
docker/gateway.Dockerfile    FROM nginx:1.27-alpine + COPY nginx.conf
docker-compose.yml           llm, api, worker, migrate, web, gateway, postgres, redis, phoenix
                             image: ${DOCKERHUB_USER}/rag-*:${IMAGE_TAG} + build: for local
                             healthchecks + depends_on: condition: service_healthy; mem_limit per service
                             profile "observability": prometheus, grafana, nginx-exporter
                             profile "gpu": llm-gpu using llama.cpp:server-cuda
compose.ci.yml               slim stack for CI integration tests
deploy/                      prometheus.yml, grafana/provisioning (datasource + RAG dashboard JSON),
                             cloudflared/config.yml.example → packaged as the release bundle
deploy/vm/                   cloud-init.yaml (provisioning), install-runner.sh, backup.sh, restore.sh, README.md
gateway/nginx.conf
Makefile                     build, push, pull, up, up-full, down, migrate, ingest, eval, eval-gate, test, load-test
src/rag_agent/
  config.py  llm.py
  ingestion/{loaders,chunker,pipeline}.py
  retrieval/{embedder,vector_store,bm25,hybrid,reranker}.py   rrf_fuse() is a pure function
  agent/{state,nodes,graph,guardrails,memory}.py
  cache/query_cache.py
  jobs/{queue,worker}.py                 arq worker, ingest task, corpus_updated pub/sub
  db/{models,session}.py + migrations/   SQLAlchemy 2 async + Alembic
  auth/{passwords,tokens,api_keys,deps}.py  FastAPI dependencies, role checks
  observability/{tracing,metrics,logging}.py
  api/{app,schemas}.py
  api/routes/{health,query,stream,ingest,feedback,auth}.py
  cli.py                     rag ingest|ask|eval|eval-gate|export-feedback|worker|create-user
web/                         Next.js (App Router, TypeScript)
  app/(auth)/login, app/chat (SSE streaming, citations panel, thumbs feedback), app/documents (upload, job status)
  lib/api.ts                 typed client, token refresh
evals/dataset.jsonl          ~15–30 {question, ground_truth, source_doc} over sample docs
evals/thresholds.yaml        CI gate thresholds
loadtest/                    k6 scenarios: smoke.js, average.js, stress.js, spike.js, soak.js, breakpoint.js, ingest_storm.js
                             locust/stream.py (SSE: TTFT + stream duration)
mock_llm/                    OpenAI-compatible mock with configurable latency / errors / 429s (compose profile loadtest)
chaos/                       toxiproxy setup, per-scenario scripts (s01_llm_saturation.py …), game_day.py
docs/                        slo.md, capacity.md, runbooks/, postmortems/ (template.md)
data/raw/                    sample docs
tests/                       unit: rrf_fuse, chunker, guardrails, graph routing (fake LLM), cache keys, auth, job idempotency
                             integration: login → upload → job done → query → cited answer → feedback
README.md                    setup, architecture diagram, Docker Hub flow, CI/CD, GPU swap notes, design trade-offs
```

## Memory budget (5.5 GB free)
| Service | mem_limit |
|---|---|
| llm | 1.2 GB |
| api | 1.0 GB |
| worker | 0.8 GB (loads embedder only) |
| web | 256 MB |
| postgres | 256 MB |
| redis | 64 MB |
| gateway | 32 MB |
| phoenix | 512 MB |
| prometheus + grafana (profile) | 2 × 192 MB |
Core stack ≈ 4.1 GB; with observability ≈ 4.5 GB. If tight: stop `observability` while developing, or run the worker only when ingesting (`docker compose run --rm worker`).

## Deploy target: local Ubuntu VM
The dev PC builds and tests; a separate VM is the "server" that CD deploys to. This practices real server work (provisioning, SSH, hardening, Docker install, runner, tunnel) and proves releases run on a clean machine. Later, the VM is swapped for a VPS with no pipeline changes except where the runner lives.

- **Hypervisor:** Multipass (`multipass launch 24.04 --name rag-prod --cpus 2 --memory 3.5G --disk 15G --cloud-init deploy/vm/cloud-init.yaml`).
- **Infrastructure as code:** `deploy/vm/cloud-init.yaml` provisions everything, so the VM can be destroyed and recreated in minutes: `deploy` user with SSH key only, password login and root SSH disabled, `ufw` (allow SSH only; the app is reached through Cloudflare Tunnel, no open web ports), `fail2ban`, unattended security upgrades, Docker Engine + compose plugin from Docker's apt repo, a 2 GB swap file, timezone, and an `/opt/rag` directory owned by `deploy`.
- **Runner:** GitHub Actions self-hosted runner installed on the VM as a systemd service under the `deploy` user, labeled `rag-prod`. `deploy.yml` uses `runs-on: [self-hosted, rag-prod]`. The runner only pulls images and runs compose; it never builds.
- **What runs on the VM:** the deploy bundle in `/opt/rag` (`docker-compose.yml`, `.env`, observability configs), plus `cloudflared` as a compose service for the public HTTPS URL.
- **RAM budget (3.5 GB VM):** use the 9Router endpoint as the primary LLM and run the local `llm` container only as an optional fallback (compose profile `local-llm`), saving ~1.2 GB. The `observability` profile stays off on the VM by default. Stop the dev stack on the host while the VM is running.
- **Secrets:** the VM's `/opt/rag/.env` is created once by hand over SSH (`chmod 600`), never committed or sent through CI.
- **Backups:** `make vm-backup` runs `pg_dump` and archives the Chroma volume to the host via `multipass transfer`; `make vm-restore` reverses it. Tested once in Verification.
- **Lifecycle commands (Makefile):** `vm-up` (launch with cloud-init), `vm-ssh`, `vm-stop`, `vm-start`, `vm-destroy`, `vm-backup`, `vm-restore`.

## Final phase: production scenarios (load, scale, resilience)
Goal: behave like a production team. For every scenario: run a **baseline**, observe the failure in Grafana/Phoenix, make the **code change**, re-run, and record before/after numbers. The system runs on the VM; the load generator runs on the host.

### Test harness (build first)
- **Mock LLM** (`mock-llm` service, compose profile `loadtest`): OpenAI-compatible, streams canned tokens with configurable per-token latency, total latency, error rate, 429 rate and timeout rate, controlled by env vars or a `/admin/config` endpoint. Without it, load tests measure 9Router's rate limits, not our system. Write it yourself (~100 lines of FastAPI); use stacklok **mockllm** and **Mocktopus** as references for the response format and lag simulation.
- **Load generator:** **k6** for REST endpoints, following its test types: smoke, average-load, stress, spike, soak, breakpoint. **Locust** for the SSE streaming endpoint, because it's Python and can measure **time to first token (TTFT)** and total stream time.
- **Fault injection:** **Toxiproxy** (Shopify) as a compose service in front of Postgres, Redis and the LLM, to add latency, timeouts and connection resets on demand; Python client in `chaos/` scripts. `docker kill` / `docker pause` for crashes.
- **SLOs** (`docs/slo.md`): non-streaming p95 < 3 s; streaming TTFT p95 < 1.5 s; error rate < 1%; ingest job done < 2 min for a 20-page PDF. **Alerts** in Prometheus/Alertmanager when an SLO burns.
- **Metrics to add before testing:** TTFT, tokens/s, in-flight LLM calls, queue depth, job age, DB pool in-use/overflow, cache hit rate, circuit breaker state, 429/503 counts, tokens spent per user.

### Scenarios that require code changes
| # | Scenario (how to simulate) | Expected failure | Code change | Reference |
|---|---|---|---|---|
| S1 | **LLM saturation**: k6 stress ramp to 50+ concurrent queries, mock LLM at 3 s/answer | In-flight LLM calls grow without bound, latency explodes, memory climbs | **Bulkhead**: `asyncio.Semaphore` per LLM endpoint + max wait time; when full, return `503` with `Retry-After` (load shedding) instead of queueing forever | Google SRE book, "Handling Overload" |
| S2 | **Slow / failing provider**: mock LLM error rate 30%, or Toxiproxy latency 10 s | Requests hang, retries amplify load (retry storm) | Per-call timeouts; retries with exponential backoff + jitter, max 2; **circuit breaker** per endpoint that opens after N failures and routes to the fallback model | `tenacity` (retries), `aiobreaker` or `purgatory` (async circuit breaker); SRE book, "Addressing Cascading Failures" |
| S3 | **Provider rate limits**: mock LLM returns 429 at >5 req/s | Errors surface to users | Honor `Retry-After`; client-side token bucket per endpoint; per-user token budget in Redis; switch to fallback when primary is limited | `aiolimiter` (async leaky bucket) |
| S4 | **Cache stampede**: warm the cache, run load, then bump `corpus_version` mid-test | Every request misses at once; LLM and DB spike | **Single-flight**: Redis `SET NX` lock per cache key so one request computes while others wait briefly or get the stale answer; jittered TTLs; stale-while-revalidate | Redis docs, distributed locks |
| S5 | **Horizontal scale**: `docker compose up --scale api=3` under stress load | Replicas disagree (BM25 index stale on some), Nginx only hits one replica | Statelessness audit: all state in Postgres/Redis/Chroma; BM25 reload via pub/sub reaches **every** replica; Nginx `resolver 127.0.0.11` so it sees all replicas; per-replica `/ready` | ADR: "API is stateless" |
| S6 | **CPU-bound models block the event loop**: stress test with cache off | Embedding/rerank in threads contend; p95 climbs even with idle LLM | Move embedder + reranker into a separate **model-service** container with **micro-batching** (collect requests for ~10 ms, run one batch); API calls it over HTTP | Hugging Face `text-embeddings-inference` (batching design) |
| S7 | **DB pool exhaustion**: soak test with 30 concurrent streams | `QueuePool limit reached` errors, requests stall | Never hold a DB session open during LLM streaming (read what you need, close, stream, then write in a new short session); size pool per replica; statement timeout; optional PgBouncer | SQLAlchemy docs, connection pooling |
| S8 | **Ingest storm**: upload 100 docs while querying | Workers starve, queue age grows, query latency rises (CPU shared) | Dedupe by content hash **before** enqueue; per-user job quota; reject with `429` when queue depth > N (backpressure); separate low-priority ingest queue; cap worker concurrency; script that scales workers on queue depth | `arq` docs; KEDA Redis scaler (concept, for k3s stretch) |
| S9 | **Concurrent writes to Chroma**: 3 workers ingesting at once | Write contention or corruption risk on embedded Chroma | Keep exactly one writer (single ingest consumer) with batched upserts; ADR to move to Chroma server mode or Qdrant if write throughput is the bottleneck | Chroma docs, client-server mode |
| S10 | **Long-lived SSE connections**: 200 idle-ish streams (slow mock LLM) | Nginx/uvicorn connection limits hit; abandoned streams keep generating | Detect client disconnect (`await request.is_disconnected()`) and **cancel** the LLM call (saves tokens); heartbeat comments every 15 s; max stream duration; tune Nginx `worker_connections` and uvicorn workers | Starlette `Request.is_disconnected` |
| S11 | **Soak 2 h**: average load | Slow memory growth, latency drift | Bounded in-process caches, capped chat history, models loaded once at startup; uvicorn `--limit-max-requests` as a safety net; memory metric alert | k6 soak test guide |
| S12 | **Redis down**: `docker stop redis` under load | App crashes or every request errors | Cache is optional (fail open with metric); rate limiter fail-open vs fail-closed decided in an ADR; ingest returns `503` when the queue is unreachable; readiness reports degraded instead of dead | — |
| S13 | **Slow Postgres**: Toxiproxy +500 ms latency | Every request slows, including ones that don't need the DB | Move non-critical writes (interaction logs, checkpoints for `direct` route) off the request path to a background task; statement timeouts; cache user/session lookups | Toxiproxy README |
| S14 | **Abusive client**: one API key at 50 req/s with 20k-character prompts | One user degrades everyone | Request size + prompt length limits; per-key quotas and token budgets; Nginx `limit_conn` per IP; block list | OWASP API Security Top 10 (resource consumption) |
| S15 | **Deploy under load**: run `deploy.yml` during an average-load test | Dropped requests and broken streams during restart | Graceful shutdown: on SIGTERM stop accepting, drain in-flight requests and streams (timeout 30 s); rolling replace (start new replica, wait `/ready`, stop old) | `docker-rollout` (zero-downtime compose deploys) |
| S16 | **Cost spike**: breakpoint test against the real 9Router model for 2 minutes only | Token spend jumps unnoticed | Tokens-per-user and per-route metrics; daily budget with alert and automatic switch to the local model when exceeded | — |
| S17 *(stretch)* | **Autoscaling**: move to k3s on the VM | Manual scaling only | Helm chart; HPA on CPU for `api`; KEDA on Redis queue length for `worker` | k3s, KEDA docs |

### Production-team practices around the scenarios
- **Runbooks** (`docs/runbooks/`): one per alert, e.g. "LLM circuit open", "queue age high", "DB pool exhausted": what it means, how to confirm, how to mitigate.
- **Postmortems** (`docs/postmortems/`): blameless write-up for each scenario that broke something: timeline, root cause, fix, follow-ups. Use the same template every time.
- **Game day**: run 3 random scenarios back to back from `chaos/game_day.py` without looking at which ones, and practise diagnosing from dashboards and runbooks only.
- **Capacity note** (`docs/capacity.md`): max sustainable users per replica on the 3.5 GB VM, what the bottleneck is at each level, and what you'd change at 10× (separate model service on GPU, managed Postgres, Qdrant, more API replicas).

## Prerequisites (user runs, need sudo / credentials)
- Install the compose plugin: `sudo apt install docker-compose-plugin` (needs Docker's apt repo) or the standalone v2 binary. Also `docker buildx` for CI-like builds.
- `docker login` before pushing (use a Docker Hub access token).
- Node 22 + pnpm for the frontend.
- GitHub repo with Actions enabled.
- Multipass installed on the host (`sudo snap install multipass`); an SSH key pair for the VM's `deploy` user.
- A runner registration token from the repo's Settings → Actions → Runners (used once inside the VM).
- Optional: Cloudflare account + `cloudflared` for a public HTTPS URL.
- Disk: ~5 GB for images + build cache. Run `docker builder prune` if it gets tight (25 GB free).

## Build order (each step runnable)
1. Scaffolding: pyproject, config, pre-commit, `scripts/export_model.sh` (copy the Ollama GGUF into `models/`), `llm` image + Phoenix in compose; check that `curl :8080/v1/chat/completions` works. **`ci.yml` with lint + unit tests from day one.**
2. Ingestion + Chroma + BM25; `rag ingest data/raw` (run locally with `uv run`).
3. Hybrid retrieval + RRF + reranker; unit tests.
4. LangGraph agent + guardrails (incl. `context_guard`); `rag ask "..."`.
5. Phoenix tracing.
6. FastAPI (`/health`, `/ready`, `/query`) + `api` image; `docker compose up`.
7. Eval: `rag eval` (Ragas) + `rag eval-gate` (deterministic retrieval metrics); add the integration + eval-gate job to `ci.yml`.
8. Postgres + Alembic + auth (users, JWT, API keys, roles).
9. Redis: async ingest worker + job status, query cache, per-user budget; conversation memory via Postgres checkpointer + `condense_question`.
10. Streaming `/query/stream` (SSE) + Next.js frontend (login, chat with citations and feedback, documents page) + `web` image.
11. Nginx gateway image + rate limits; Cloudflare Tunnel for a public URL.
12. Observability: Prometheus metrics, JSON logs, Grafana dashboard (latency per node, cache hit rate, route mix, retries, guard blocks); k6 load test, record p95 in README.
13. VM + CD: write `deploy/vm/cloud-init.yaml`, `make vm-up`, verify hardening, install the runner on the VM, create `/opt/rag/.env`; then `release.yml` (build, Trivy, push, deploy bundle) and `deploy.yml` (runs on the VM runner: pull, up, `/ready`, smoke test, rollback). **First Docker Hub push only after you confirm, since it's a public action.**
14. README with architecture diagram and design trade-offs. Run `graphify update .` after code changes (per CLAUDE.md).
15. **Final phase, production scenarios** (see section above): first the harness (mock LLM, k6 + Locust, Toxiproxy, SLOs, new metrics, alerts), then scenarios S1–S16 one at a time: baseline → failure → code change → re-run → numbers in `docs/benchmarks.md`, postmortem if something broke, runbook for each new alert. Finish with a game day and `docs/capacity.md`. S17 (k3s autoscaling) is optional.

## Verification
- `uv run pytest`: unit tests pass (RRF ordering, chunk IDs stay the same across runs, router fallback, retry loop stops at 2, cache key changes with `corpus_version`, role checks, ingest job idempotent on re-run).
- `docker compose up -d` → all services healthy; `curl localhost/api/ready` through the gateway.
- Web app: log in, upload a doc, job goes `queued → running → done`, ask a doc-specific question, tokens stream, citations point to the uploaded file, a greeting takes the `direct` route, a follow-up question uses chat history.
- Asking the same question twice: second response is a cache hit (visible in metrics and response header `X-Cache: HIT`); after a new ingest it's a miss again.
- Hammering `/api/query/stream` returns 429 after the burst.
- Phoenix at `localhost:6006` shows one trace per query with node spans; the `trace_id` returned to the UI matches.
- Grafana at `localhost:3001` shows request rate, p95 latency, cache hit rate.
- `make eval-gate` passes thresholds; `docker compose run --rm api rag eval` writes `evals/results/<timestamp>.csv`.
- CI: a PR that breaks retrieval (e.g. `top_k=1`) fails the eval gate.
- CD: tagging `v0.1.0` pushes images, creates the release bundle, deploys, and passes the smoke test; deploying a deliberately broken tag rolls back automatically.
- Fresh-pull test: `make vm-destroy && make vm-up` → install runner, add `.env` → a release deploy works on the brand-new VM with no source or build.
- VM hardening: SSH with a password is refused, root SSH is refused, `ufw status` shows only SSH allowed, `docker` runs without sudo for `deploy`.
- Backup/restore: `make vm-backup`, destroy and recreate the VM, `make vm-restore` → previous documents and users are back.
- `docker stats`: core stack stays under ~4.2 GB.
- Final phase: every scenario S1–S16 has a before/after row in `docs/benchmarks.md`; SLOs in `docs/slo.md` hold under the average-load test; under the stress test the system sheds load with 503/429 instead of timing out; killing an API replica or Redis during load causes no crash and recovers automatically; a deploy during load drops zero requests; game day completed using only dashboards and runbooks.
