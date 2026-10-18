# Best Practices by Phase (adapted from reference repos)

Companion to `PLAN.md`. Each practice names the repo it comes from, the tool that repo used, and the
equivalent in our stack. We adopt the *practice*, not the code.

Reference repos:
- **[AR]** uehlingeric/agentic-rag — agentic RAG reference system, ADRs, judged benchmarks, red-team suite
- **[VS]** vstorm-co/full-stack-ai-agent-template — FastAPI + Next.js production template (MIT, ~2k stars)
- **[FD]** tonystalker/FlowDesk — LangGraph support agent, hybrid RAG, confidence-based retry, CI → Cloud Run
- **[CR]** charan-ravikumar/Advanced-Rag + Multi-Agent-AI-Research-Analyst — retrieval ablation study, eval harness

---

## Phase 0 — Project process (applies throughout)
| Practice | Source (their tool) | Ours |
|---|---|---|
| Record every significant decision as an ADR (context, options, decision, consequences) | [AR] 9 ADRs in repo | `docs/adr/NNNN-title.md`. Seed list: 0001 llama.cpp over SGLang (no GPU), 0002 Chroma + BM25 over Qdrant, 0003 SSE over WebSocket, 0004 RRF k=60, 0005 rerank-score grading over LLM grading, 0006 deterministic CI gate, 0007 9Router primary + local fallback, 0008 single-writer Chroma |
| Ship plans and honest limitations, not just features | [AR] weekly plans, `docs/benchmarks.md`, `docs/limitations.md` | `docs/plans/`, `docs/benchmarks.md`, `docs/limitations.md` (e.g. "0.5B fallback answers are weak", "Ragas judge is noisy") |
| SemVer + CHANGELOG from the first release | [AR] stable SemVer at v1.0.0; [VS] CHANGELOG | `CHANGELOG.md` (Keep a Changelog format), tags `vX.Y.Z` drive `release.yml` |
| One command demo with zero cloud dependencies, timed on a clean machine | [AR] `make demo`, "clone to first cited answer in 23 s" | `make demo` = llm + api + web + gateway + sample docs pre-ingested; record the time in README |
| AI-assistant-friendly repo docs | [VS] `CLAUDE.md`, `AGENTS.md`, `.claude/skills` | Keep `CLAUDE.md` current (graphify already set up). No `AGENTS.md`: Zed reads `CLAUDE.md` by default, and an `AGENTS.md` would replace it |
| Dependency update bot, security policy | [VS] `renovate.json`, `SECURITY.md` | Renovate (or Dependabot) for pip, npm, Docker base images; short `SECURITY.md` |

## Step 1 — Scaffolding, config, CI skeleton
| Practice | Source | Ours |
|---|---|---|
| Layered backend: routes → services → repositories | [VS] Repository + Service pattern | `api/routes/` (HTTP, validation, auth only) → `services/` (business logic, calls the graph) → `db/repositories/` (queries). Routes never touch the ORM directly |
| Versioned API paths | [VS] `api/routes/v1/` | `/api/v1/...` from day one; gateway rules match `/api/v1/` |
| Central config + dependency injection | [VS] `core/config`, `deps.py`; [FD] `config.py` | `config.py` (pydantic-settings) + `api/deps.py` for DB session, current user, LLM client |
| Three compose environments | [VS] `docker-compose.dev.yml` (hot reload, bind mounts), `docker-compose.yml` (prod-like on localhost), `docker-compose.prod.yml` | Same three files; `make dev`, `make stage`, `make prod`. "stage" is what CI integration tests and the fresh-pull test use |
| Idempotent bootstrap | [VS] `make bootstrap`: build, start, wait `pg_isready`, migrate, seed admin; safe to re-run | `make bootstrap`: export model, build, up, wait healthy, `alembic upgrade head`, `rag create-user --admin`, ingest sample docs |
| Pre-commit + lint + tests in CI from the first commit | [VS] pre-commit hooks; [FD] ruff + pytest before build | ruff, mypy, gitleaks, prettier pre-commit; `ci.yml` runs them plus unit tests |

## Step 2 — Ingestion
| Practice | Source | Ours |
|---|---|---|
| Never commit generated indexes | Anti-pattern seen in [FD] (`bm25_index.pkl` in git) | BM25 rebuilt from Chroma at startup/after ingest; `.gitignore` all index/model artifacts |
| Structure-aware chunking | [CR] spaCy semantic chunking; [VS] recursive / markdown / fixed splitters | Start with recursive splitting on headings → paragraphs → sentences; keep `source`, `page`, `heading_path` metadata on every chunk for citations. Treat chunker choice as an ablation variable (Step 7) |
| Same ingestion code for CLI, API and scheduled sync | [VS] CLI `rag-ingest` + upload + sync sources | One `IngestionPipeline`, called by `rag ingest`, the worker job, and (later) a scheduled sync |

## Step 3 — Hybrid retrieval + rerank
| Practice | Source | Ours |
|---|---|---|
| Dense + sparse + RRF + cross-encoder | [FD], [CR], [AR] all converge on this | Unchanged: Chroma top20 + BM25 top20 → RRF k=60 → top10 → `ms-marco-MiniLM-L-6-v2` → top4 |
| Graceful degradation | [FD] falls back to sparse-only search if the embedding API is unreachable | If the embedder fails → BM25-only; if the reranker fails → RRF order. Emit a `degraded_mode` metric and span attribute |
| Make retrieval variants pure config, not code | [CR] 4 ablation configs as parameter variants to avoid implementation confounds | `retrieval.mode: dense \| bm25 \| hybrid \| hybrid_rerank` in `config.yaml`; one code path |

## Step 4 — LangGraph agent + guardrails
| Practice | Source | Ours |
|---|---|---|
| Confidence-gated retry that changes strategy, not just the query | [FD] confidence < 0.6 → retry with wider search and a stronger model | On `grade` failure: rewrite query **and** widen `top_k` (20 → 40); on the final attempt escalate from local model to the 9Router model |
| Route by complexity to different models | [FD] Groq for short/simple, Gemini for complex/retry | `router` also outputs `complexity: simple \| complex`; simple → fast model, complex → stronger model (both via `LLM_*` config) |
| Honest refusal is a first-class outcome | [AR] "citation-grounded answer or an honest refusal"; measures false refusals | If grading is exhausted, answer "not found in the documents" with closest sources. Track `refusal_rate` and **false refusals** in evals |
| Bounded loops, proven terminating | [CR] bounded self-critique loop | `attempts < 2` hard cap in state; unit test that the graph always reaches END |
| Keep a vanilla pipeline to compare against the agent | [AR] vanilla pipeline vs LangGraph loop; the loop helped strong models and *hurt* the local 8B model | `pipeline: vanilla \| agent` flag. Benchmark both per model; likely finding: agent loop only pays off on the 9Router model |
| Red-team suite for guardrails | [AR] input/output guardrails + red-team attack suite | `tests/redteam/attacks.jsonl` (prompt injection in queries and in documents, data exfiltration, jailbreaks); CI asserts block rate and that 0 benign eval questions are blocked |
| Human escalation path | [FD] escalation agent for human handoff | Out-of-scope or low-confidence answers get a "flag for review" button; flagged items land in the admin feedback view |

## Step 5 — Tracing
| Practice | Source | Ours |
|---|---|---|
| One span per pipeline stage | [AR] OTel span per stage → Jaeger | openinference OTel → Phoenix; one span per graph node with attributes: `route`, `attempt`, `top_k`, `max_rerank_score`, `model`, `degraded_mode` |
| Trace the whole stack, not just the LLM | [VS] Logfire instruments FastAPI, DB, Redis, queue, HTTPX in one timeline | Add `opentelemetry-instrumentation-fastapi`, `-sqlalchemy`, `-redis`, `-httpx`; export to Phoenix (OTel-compatible) so an API request and its LLM spans share one trace |

## Step 6 — API + provider abstraction
| Practice | Source | Ours |
|---|---|---|
| Providers behind one protocol | [AR] Anthropic/Google/OpenAI/Ollama adapters behind one protocol; local path needs no keys | `llm.py`: `LLMClient` protocol with `chat()`, `chat_stream()`, `chat_json()`; one OpenAI-compatible implementation, configured as `primary` (9Router) and `fallback` (llama-server). Timeout + circuit breaker per endpoint |
| Readiness covers every dependency | [VS] system health checks API, DB, Redis, vector store, LLM, worker | `/ready` checks Postgres, Redis, Chroma, primary LLM, fallback LLM, worker heartbeat; an admin "System" page shows the same |

## Step 7 — Evaluation
| Practice | Source | Ours |
|---|---|---|
| Ablation study with a deterministic harness | [CR] 4 configs; Recall@K, MRR, P50/P95/P99 latency; RAGAS as an optional layer; isolated that the gain came from RRF fusion, not BM25 alone | `rag eval ablate` runs `dense`, `bm25`, `hybrid`, `hybrid_rerank` × `vanilla`/`agent`; outputs Recall@4, MRR, P50/P95/P99, refusal rate to `docs/benchmarks.md` |
| Evaluate the agent loop itself, not just retrieval | [CR] eval harness caught self-correction dropping faithfulness 93.3% → 39.1% from an ambiguous prompt | Compare faithfulness with `rewrite_query` on vs off; any prompt change re-runs the eval before merge |
| Calibrate the LLM judge | [AR] LLM-as-judge benchmarks with calibration data | Hand-label ~30 answers (correct / partial / wrong); report judge agreement with your labels in `docs/benchmarks.md`. Only trust Ragas metrics the judge agrees on |
| Publish numbers from the production path | [AR] benchmarks run with guardrails on | Evals run through the same API code path, guardrails on |

## Step 8–9 — Auth, Postgres, Redis, async jobs, memory
| Practice | Source | Ours |
|---|---|---|
| JWT + refresh in httpOnly SameSite cookies, auto-refresh in the client | [VS] | Same; API keys (`sk_` prefix, stored hashed) for CLI and scripts |
| Sliding-window rate limits per user and per IP | [VS] per user / org / IP | Redis sliding window per user in the API, plus Nginx per-IP limits |
| Log every interaction for LLMOps | [FD] PostgreSQL log of confidence, groundedness, thumbs feedback | `interactions` table: query, route, model, attempts, max rerank score, latency, cache hit, trace_id, rating |
| Feedback analytics | [VS] message ratings with admin analytics | Admin page: approval rate, downvoted queries, one click to export to the eval set |
| Migrations run before app start, never by hand in prod | [VS] bootstrap migrates; [FD] Alembic | One-shot `migrate` service in compose; CI checks `alembic upgrade head` on a fresh DB |

## Step 10 — Streaming + frontend
| Practice | Source | Ours |
|---|---|---|
| Typed streaming event protocol | [VS] events like `text_delta` over WebSocket | SSE events `route`, `sources`, `token`, `done`, `error` with a shared TypeScript type; ADR explains SSE over WebSocket (one-way, simpler through Nginx and Cloudflare) |
| Frontend structure | [VS] `hooks/` (`useChat`, `useWebSocket`), Zustand `stores/`, `components/` | `hooks/useChatStream`, `stores/session`, `components/chat`, `components/sources-panel` |
| Citations panel and source preview | [VS] citation sources panel | Clicking a citation opens the chunk with its page number |
| End-to-end browser tests | [VS] Playwright `e2e/` | Playwright: login → upload → ask → streamed answer with citation → thumbs up |

## Step 11–13 — Gateway, observability, CD
| Practice | Source | Ours |
|---|---|---|
| Lint → test → build → deploy on main | [FD] ruff, pytest, Docker build, deploy to Cloud Run | Same order, plus Trivy scan and eval gate; deploy via self-hosted runner instead of Cloud Run |
| Secrets only in CI secrets and `.env`, documented | [FD] lists required GitHub secrets in README | README table of every secret and where it lives; `.env.example` has every key with no values |
| Gateway config shipped with the project | [VS] `nginx/nginx.conf` as reference for prod | Baked into `rag-gateway` image |
| Version metadata in the build | [VS] generator version and timestamp in `pyproject.toml` | Image labels (`org.opencontainers.image.version`, `revision` = git SHA); `/health` returns version and SHA |

---

## Deliberately not adopted
- **Multi-agent planner/retriever/synthesizer/verifier** [AR]: adds 2× cost and latency; their own benchmarks show it hurts small models. Revisit only if evals on the 9Router model justify it (ADR).
- **Billing, teams, marketing site** [VS]: out of scope for a learning project.
- **Managed vector DB (Pinecone)** [FD]: conflicts with offline pull-and-run; Chroma stays.
- **Copying code**: only patterns. Check each repo's license before reusing any snippet ([VS] is MIT; others must be checked).
