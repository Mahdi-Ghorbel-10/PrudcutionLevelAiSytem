# Answer key: B1 Scaffolding (Tutor only)

Do not show this file to Mahdi before grading.

| Q | Answer | Type |
|---|---|---|
| 1 | B | why |
| 2 | C | what breaks if |
| 3 | A | why |
| 4 | C | why |
| 5 | A | why |
| 6 | B | why |
| 7 | B | what breaks if |
| 8 | B | why |
| 9 | A | what breaks if |
| 10 | C | why |
| 11 | B | why |

## Q1. Tunables in YAML, URL in `.env`. Answer: B
- **B (correct).** `config.yaml` holds values shared by every environment (`llm_timeout_seconds: 30`). `.env` holds per-machine values and secrets. Example: the same timeout on laptop and VM, but a different `LLM_BASE_URL` on each.
- A: Load speed is not the reason. Wrong because the split follows who changes the value, not parse speed.
- C: Wrong. `Tunables` is a pydantic model too, and `load_tunables` validates it with `model_validate`.
- D: Wrong. Secrets belong in `.env`, which is gitignored. Only `.env.example` (no values) is committed.

## Q2. No `.env`, no shell variable. Answer: C
- **C (correct).** `Settings` has `llm_base_url: str = Field(min_length=1)` with no default, so pydantic raises `ValidationError` inside `load_config`, at startup. Example: `python -c "from rag_agent.config import load_config; load_config()"` fails right away.
- A: Wrong. The code has no default URL. `.env.example` is only a template.
- B: Wrong. This is the failure the design avoids. Errors are deferred to the first request in apps without fail-fast checks.
- D: Wrong. `llm_model` has a default, but `llm_base_url` does not, so the missing URL still fails.

## Q3. Empty `LLM_BASE_URL=""`. Answer: A
- **A (correct).** An empty string is a valid `str`. The `min_length=1` constraint is what rejects it. `test_empty_required_env_fails_fast` exists because someone could remove the constraint and the missing-value test would still pass. Example: `LLM_BASE_URL=` in `.env` would otherwise start the app with an empty endpoint.
- B: Wrong. pydantic raises a validation error. It does not crash the process.
- C: Wrong. `llm_model` is a separate field with its own default.
- D: Wrong. `.env` values are read as written, empty values included. That is why the empty case needs its own test.

## Q4. `env_file=None` in tests. Answer: C
- **C (correct).** `load_config(env_file=".env")` by default. If a developer has a real `.env` with a working URL, a test expecting the "missing" error would pass or fail depending on their machine. Passing `None` makes the test read only the environment it sets with `monkeypatch`.
- A: Wrong. The YAML path is passed explicitly in every test (`_write_tunables`).
- B: Wrong. The speed of YAML parsing is not the point.
- D: Wrong. `.env` is still read in production. The parameter exists only so tests can switch it off.

## Q5. Pinned llama.cpp tag. Answer: A
- **A (correct).** `ghcr.io/ggml-org/llama.cpp:server-b11718` names one build. `latest` moves whenever upstream publishes, so the same Dockerfile can build a different server on a different day. This is decision D2 in the spec.
- B: Wrong. No such Docker Hub rule exists. The reason is reproducibility, not policy.
- C: Wrong. The tag has no effect on image size.
- D: Wrong. `--jinja` is a runtime flag. The pin is about reproducibility, not flags.

## Q6. Copy instead of re-download. Answer: B
- **B (correct).** The Ollama blob is the same bytes as the model Ollama already has, so no second download is needed. The `sha256-<hash>` name in the blob path gives the expected checksum, and `sha256sum` on the copy verifies it. Example: a mismatch means the copy is corrupt.
- A: Wrong. The copy is identical by design. A different file would fail the checksum.
- C: Wrong. Ollama blobs are plain GGUF files. Nothing is encrypted.
- D: Wrong. The Dockerfile still needs `COPY`, because `models/` is what gets baked into the image.

## Q7. Checksum mismatch. Answer: B
- **B (correct).** The script runs `set -euo pipefail` and has an explicit `exit 1` after the mismatch message. The bad file is not deleted, so a careless next step (like `docker build`) could use it. The build only goes ahead when the script exits 0.
- A: Wrong. The script never deletes `DEST`. It only exits with an error.
- C: Wrong. There is no retry loop.
- D: Wrong. The check exits 1, so `&&` chains and `make` stop.

## Q8. Two bind addresses. Answer: B
- **B (correct).** Inside the container, `127.0.0.1` means only the container itself. Docker's port forwarding comes in on the container's network interface, so the server must listen on `0.0.0.0`. On the host, the publish `127.0.0.1:8081:8080` means only the dev PC can reach it.
- A: Wrong. `0.0.0.0` means all interfaces. `127.0.0.1` means loopback only.
- C: Wrong. Compose does not require it. Phoenix has its own binding.
- D: Wrong. The host-side `127.0.0.1` is what keeps the port off the network. The container-side `0.0.0.0` only means "all interfaces inside the container".

## Q9. Remove `--host 0.0.0.0`. Answer: A
- **A (correct).** llama.cpp listens on `127.0.0.1` by default. The healthcheck runs inside the container, so it still reaches `localhost:8080` and passes. Docker's port forwarding can't reach a loopback-only server, so `curl localhost:8081` from the host fails. This is a good "passes in CI, broken on the host" case.
- B: Wrong. The model loads from the file path given in `-m`, which is unaffected.
- C: Wrong. The healthcheck is inside the container, so it still passes.
- D: Wrong. The default is `127.0.0.1`, so removing the flag changes behaviour.

## Q10. Port 8081. Answer: C
- **C (correct).** The comment in `docker-compose.yml` says 8080 is taken by Jenkins on the dev PC. The container still listens on 8080 internally, and `LLM_HOST_PORT` overrides the host port.
- A: Wrong. The server does not care which host port is used.
- B: Wrong. The healthcheck uses `localhost:8080` inside the container, not the host port.
- D: Wrong. Docker does not reserve 8080.

## Q11. gitleaks as a pre-commit hook. Answer: B
- **B (correct).** Once a secret is committed, it stays in history even after deletion, so the key must be rotated. Stopping it before the commit is much cheaper.
- A: Wrong. Formatting is done by ruff-format, not gitleaks.
- C: Wrong. Nothing in GitHub requires it. It is a local choice.
- D: Wrong. CI runs ruff, mypy and pytest. gitleaks does not replace the test job.

## Teaching note (tutor only)
`ci.yml` does not run gitleaks. The check exists only as a local pre-commit hook, so a contributor who skips `pre-commit install` gets no secret scan in CI. Use this as a follow-up question after grading, for example: "What would you add to `ci.yml` to close that gap?"
