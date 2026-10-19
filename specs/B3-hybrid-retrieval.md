# Spec: B3 Hybrid retrieval

Status: approved (2026-10-19, user approved D1 to D7 with the recommended options) (`draft` → `approved` → `building` → `review` → `done`)
Board row: `COLLABORATION.md` → B3
Design context: `PLAN.md` → Architecture ("Request flow": hybrid_retrieve and rerank), Key design decisions (sync models in `asyncio.to_thread`), Layout (`retrieval/{hybrid,reranker}.py`, `rrf_fuse()` is a pure function), Build order step 3. Best practices: `BEST_PRACTICES.md` → Step 3 (graceful degradation, retrieval variants as config).

## Goal
`retrieve(query)` returns the best chunks for a question by combining dense search (Chroma), keyword search (BM25, from B2) and a cross-encoder reranker. The mode is set in `config.yaml`, so B7 can compare dense, BM25, hybrid and hybrid with rerank without code changes. If the embedder or reranker fails, the query still returns results and says which stage degraded.

## Substeps
Each substep is one commit and one testable behaviour. The builder ticks it in `handoffs/B3.md`, with its done-check result, only when the check passes. The boxes in this spec stay unticked.

- [ ] **1. RRF fusion.** Files: `src/rag_agent/retrieval/hybrid.py` with `rrf_fuse(rankings, k) -> list[tuple[str, float]]`, a pure function over ranked lists of chunk IDs. Score per ID = sum of `1 / (k + rank)`, rank starting at 1. Done-check: unit test with two hand-made rankings gives the expected order, and an ID found by both lists beats an ID found by one list at the same rank.
- [ ] **2. Dense search.** Files: `src/rag_agent/retrieval/vector_store.py` (add `query(embedding, k)` returning chunk IDs in rank order with their stored text), `src/rag_agent/retrieval/embedder.py` (`embed_query(text)` for one string). Done-check: unit test on a temporary Chroma store with three chunks returns the nearest chunk first.
- [ ] **3. Hybrid retriever.** Files: `src/rag_agent/retrieval/hybrid.py` (`HybridRetriever` with `retrieve(query) -> RetrievalResult`). It runs dense top 20 and BM25 top 20, fuses with RRF, and keeps the top 10. The BM25 index is built from the vector store at construction time (per D7 in B2). The `mode` decides which stages run: `dense`, `bm25`, `hybrid`, `hybrid_rerank`. Done-check: unit tests with a fake embedder show that `bm25` never calls the embedder and `dense` never reads BM25 results, and that `hybrid` returns the RRF top 10.
- [ ] **4. Reranker.** Files: `src/rag_agent/retrieval/reranker.py` (`Reranker` wrapping `sentence-transformers` `CrossEncoder`, `rerank(query, candidates, top_k)` returns `(chunk, score)` pairs, best first). Runs in `asyncio.to_thread` when called from async code. Done-check: unit test with a fake model checks the order follows the scores and the output has `top_k` items. A `slow` test with the real `cross-encoder/ms-marco-MiniLM-L-6-v2` ranks a matching passage above an unrelated one.
- [ ] **5. Graceful degradation.** Files: `src/rag_agent/retrieval/hybrid.py`. If the embedder raises, the query runs as BM25 only. If the reranker raises, the RRF order is returned. `RetrievalResult` has a `degraded` list naming the failed stage (`embedder`, `reranker`) and is empty on a clean run. Done-check: unit test with an embedder that raises returns BM25 results with `degraded == ["embedder"]`, and a reranker that raises returns the RRF order with `degraded == ["reranker"]`.
- [ ] **6. Retrieval config.** Files: `config.yaml` (new `retrieval` section), `src/rag_agent/config.py` (`RetrievalTunables`, pydantic, rejects unknown modes and a `fused_top` larger than the two candidate lists combined). Values: `mode: hybrid_rerank`, `dense_top_k: 20`, `bm25_top_k: 20`, `rrf_k: 60`, `fused_top_k: 10`, `rerank_top_k: 4`, `rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2`. Done-check: config test loads the defaults, and a test with `mode: bogus` fails at startup with a clear message.
- [ ] **7. Search command.** Files: `src/rag_agent/cli.py` (`rag search "QUERY"` prints each result with rank, score, source, page and `degraded` stages), `tests/test_cli.py`. Done-check: after `uv run rag ingest data/samples`, `uv run rag search "copperkettle"` ranks the chunk from its sample file first.
- [ ] **8. Unit tests and CI.** Files: tests for each substep above. The slow reranker test is marked `slow` (skipped in CI, per B2). Done-check: `uv run pytest` passes with the new tests, and `uv run pytest -m slow` passes locally.

## Out of scope
- The LangGraph agent, the `grade` threshold and the `rewrite_query` retry loop (B4). This step only returns scores. It does not decide if they are good enough.
- Query cache, auth and the API (B6, B8, B9).
- Phoenix spans and a `degraded_mode` metric. This step only returns `degraded` in the result. Tracing and metrics come in B5 and B12.
- Eval metrics such as hit rate and MRR (B7). The `rag search` output is for checking by hand.
- Baking the reranker into the `api` image (B6). It downloads on first use here.

## Decisions needing approval
- [x] **D1. Reranker model.** Recommended: `cross-encoder/ms-marco-MiniLM-L-6-v2` (~90 MB, already in PLAN, fast on this CPU). Alternative: a larger cross-encoder such as `BAAI/bge-reranker-base`. It is usually more accurate, but slower per query on this CPU, and the download is bigger.
- [x] **D2. Candidate counts.** Recommended: dense 20, BM25 20, fused 10, final 4, as in PLAN. All are config values, so B7 can change them. Alternative: smaller candidate lists (10 and 10) to make the reranker faster, at some cost in recall.
- [x] **D3. Retrieval modes in config.** Recommended: one code path with `mode: dense | bm25 | hybrid | hybrid_rerank` (BEST_PRACTICES Step 3). Alternative: separate classes per mode, which is more code and makes ablations harder to read.
- [x] **D4. Where degradation is reported.** Recommended: `RetrievalResult.degraded` list, returned to the caller and printed by `rag search`. Metrics and span attributes wait for B5 and B12. Alternative: log a warning only, which is simpler but leaves the caller unable to tell.
- [x] **D5. Reranker call.** Recommended: run in `asyncio.to_thread`, as the embedder does (PLAN). Alternative: call it inline, which is simpler, but it blocks the event loop once the API exists (B6).
- [x] **D6. Scores returned, no threshold.** Recommended: return rerank scores; the grading threshold belongs to B4, where the agent uses it. Alternative: put a default threshold here, which would make B4's design choice for it.
- [x] **D7. `rag search` command.** Recommended: add it in substep 7, so you can see retrieval work before the agent exists (B4). Alternative: skip it and check retrieval only with unit tests until `rag ask` in B4.

## Prerequisites (user)
- Network access on first use of the reranker. `cross-encoder/ms-marco-MiniLM-L-6-v2` (~90 MB) is downloaded from Hugging Face. The first run of `rag search` and the slow test need it.
- Step 2 must be ingested first: `uv run rag ingest data/samples`.

## Done when
- All eight substeps are ticked, and each done-check result is in the handoff.
- `uv run pytest` passes and CI is green on the PR. The `slow` reranker test passes locally.
- `uv run rag search "copperkettle"` ranks the right sample file first. The output is pasted into the handoff.
- Handoff note in `handoffs/B3.md` lists files touched, commands run, and the `rag search` output for two queries, one keyword and one meaning-based.

## Change log
- 2026-10-19: Draft created from PLAN build order step 3 and BEST_PRACTICES Step 3.
- 2026-10-19: D1 to D7 approved with the recommended options. Status set to approved.
