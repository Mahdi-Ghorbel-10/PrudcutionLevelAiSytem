# Spec: B2 Ingestion

Status: approved (2026-10-19, user approved D1 to D7)
Board row: `COLLABORATION.md` → B2
Design context: `PLAN.md` → Architecture ("Key design decisions": IngestionPipeline, content-hash IDs, BM25 rebuilt from Chroma), Layout (`ingestion/`, `retrieval/`), Build order step 2. Best practices: `BEST_PRACTICES.md` → Step 2 (no generated indexes in git, structure-aware chunking, one ingestion code path).

## Goal
`rag ingest <path>` reads txt, md, pdf and docx files, splits them into chunks that keep their source, page and heading path, embeds them into a local Chroma store, and rebuilds an in-memory BM25 index. Running the same ingest twice changes nothing. After this step, a keyword query finds the right chunk in the sample documents.

## Substeps
Each substep is one commit and one testable behaviour. Tick a box only when its done-check passes.

- [ ] **1. Loaders.** Files: `src/rag_agent/ingestion/loaders.py` (returns `Document(text, source, page)` for txt, md, pdf (pypdf, one document per page) and docx (python-docx)), `tests/fixtures/` (one small pdf and one docx, under 20 KB each). Done-check: unit tests load each format and check the text and page numbers.
- [ ] **2. Chunker.** Files: `src/rag_agent/ingestion/chunker.py`. Splits on headings, then paragraphs, then sentences, to a size from `config.yaml` with overlap. Each chunk keeps `source`, `page` and `heading_path`, and gets an `embed_text` per D7 (the heading path and the text when `embed_with_heading` is true, otherwise the text alone). Done-check: unit tests check size limits, overlap, that a heading path follows nested headings, and that `embed_text` starts with the heading path only when the flag is on.
- [ ] **3. Chunk IDs.** Files: inside `chunker.py` or a small `ids.py`. ID = sha256 of source, heading path and chunk text. Done-check: unit test shows the same input gives the same IDs across runs, and an edited chunk gets a new ID.
- [ ] **4. Vector store.** Files: `src/rag_agent/retrieval/vector_store.py` (Chroma `PersistentClient` at `data/chroma/`, `upsert` only, never `add`). The stored document is the raw `text`, and the vector comes from `embed_text`. Done-check: unit test upserts the same chunks twice and the count stays the same, and a stored document equals the raw text.
- [ ] **5. Embedder.** Files: `src/rag_agent/retrieval/embedder.py` (`BAAI/bge-small-en-v1.5` through sentence-transformers, CPU, batched, run in a thread pool so it does not block async code later). The embedder takes `embed_text`, not `text`. Adds the CPU torch index to `pyproject.toml` through `[tool.uv.sources]`, per decision D5. Done-check: a test marked `slow` embeds two sentences and gets 384-dimensional vectors, and a unit test with a fake model checks that the embedder receives `embed_text`. `slow` tests are skipped in CI.
- [ ] **6. BM25 index.** Files: `src/rag_agent/retrieval/bm25.py`. Built from `embed_text` for every chunk in the Chroma collection on startup and after each ingest, so keyword search sees the same text as the vectors (per D7). Done-check: unit test on a few chunks returns the chunk that contains a rare word from the query first.
- [ ] **7. Pipeline and CLI.** Files: `src/rag_agent/ingestion/pipeline.py` (`IngestionPipeline.run(path) -> IngestReport`, used by the CLI now and by the worker in B9), `src/rag_agent/cli.py` (`rag ingest PATH`, prints files, chunks added and chunks skipped), a `[project.scripts]` entry `rag` in `pyproject.toml`. Done-check: `uv run rag ingest data/samples` prints a count. A second run prints 0 chunks added.
- [ ] **8. Sample documents.** Files: `data/samples/` with 4 to 6 short files (txt, md, one pdf, one docx) on a few topics, each with a distinct rare keyword. `.gitignore` keeps `data/chroma/` and `data/raw/` out of git. Done-check: `uv run rag ingest data/samples` finishes, and a script or test finds each rare keyword in the BM25 results.
- [ ] **9. Tests in CI.** Files: `pyproject.toml` (register the `slow` marker and set CI to skip it). Done-check: `ci.yml` still passes on the B2 pull request, and the slow embedding test runs locally with `uv run pytest -m slow`.

## Out of scope
- Hybrid retrieval, RRF, and the reranker (B3).
- The API, the worker, the job queue, and `corpus_updated` pub/sub (B6, B9).
- Scheduled sync of sources (later). Chroma server mode (only if write throughput needs it, S9).
- Docker image changes for the api (B6). The embedding model is downloaded on first run here. Baking it into an image comes with B6.
- Evals (B7).

## Decisions needing approval
- [x] **D1. Embedding library.** Recommended: sentence-transformers with CPU torch. It is the standard API for bge models. Alternative: fastembed (ONNX, no torch, smaller install, but a different model loader).
- [x] **D2. Chunk size and overlap.** Recommended: 800 characters with 100 overlap, as tunables in `config.yaml`. They are an ablation variable in B7. Alternative: token-based sizes, which need a tokenizer.
- [x] **D3. BM25 library.** Recommended: `rank-bm25`, which is small and simple to read. Alternative: `bm25s`, which is faster on larger corpora but adds a dependency.
- [x] **D4. Sample documents location.** Recommended: `data/samples/` is tracked in git (small, public), and `data/raw/` stays gitignored for your own documents. Alternative: keep everything in `data/raw/` and gitignore it.
- [x] **D5. CPU torch index.** Recommended: add it now, in substep 5, as the plan says. This is the change deferred from B1. Alternative: keep torch on the default index, which pulls the CUDA build (~5 GB).
- [x] **D6. CLI framework.** Recommended: Typer, for typed commands and help text. Alternative: argparse, which needs no dependency.
- [x] **D7. Heading in the embedded text.** Recommended: prepend the heading path to the text that is embedded (`Leave Policy > Parental leave`, a newline, then the chunk text), store the raw text as the document, and have BM25 index the same embedded text. A flag `embed_with_heading: true` in `config.yaml` lets B7 compare with and without. Alternative: embed the raw text only, as before this decision.

## Prerequisites (user)
- Network access on first run. The embedding model (~130 MB) is downloaded from Hugging Face. The CPU torch wheel is ~200 MB.
- No Docker or Ollama changes are needed for this step.

## Done when
- All nine substeps are ticked, and each done-check result is in the handoff.
- Unit tests pass in CI. The `slow` embedding test passes locally.
- `git ls-files` shows no `data/chroma/`, `data/raw/` or index files. `data/samples/` is tracked.
- Handoff note in `COLLABORATION.md` lists files touched, commands run, the ingest output, and the keyword-search results.

## Change log
- 2026-10-18: Draft created from PLAN build order step 2 and BEST_PRACTICES Step 2. Notes the conflict between PLAN's "`data/raw/` sample docs" and the `data/raw/` gitignore added during planning, resolved by D4.
- 2026-10-19: D7 added and approved (heading path in the embedded text, BM25 on the same text, `embed_with_heading` flag). Substeps 2, 4, 5 and 6 updated to match. Status set to approved, and the user approved D1 to D7.
