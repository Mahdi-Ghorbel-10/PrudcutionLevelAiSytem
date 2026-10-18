# Answer key: B1 Scaffolding (Tutor only)

Do not show this file to Mahdi before grading.

| Q | Answer | Type |
|---|---|---|
| 1 | B | why |
| 2 | C | what breaks if |
| 3 | A | why |
| 4 | D | why |
| 5 | A | why |
| 6 | C | why |
| 7 | B | what breaks if |
| 8 | C | why |
| 9 | D | what breaks if |
| 10 | C | why |
| 11 | D | why |
| 12 | A | why |

## Q1. Tunables in YAML, URL in `.env`.
- **B (correct).** `config.yaml` holds values shared by every environment (`llm_timeout_seconds: 30`). `.env` holds per-machine values and secrets. Example: the same timeout on laptop and VM, but a different `LLM_BASE_URL` on each.
- A: Wrong. Load speed is not the reason. The split follows who changes the value, not parse speed.
- C: Wrong. `Tunables` is a pydantic model too, and `load_tunables` validates it with `model_validate`.
- D: Wrong. Secrets belong in `.env`, which is gitignored. `config.yaml` is committed, so secrets there would reach git.

## Q2. No `.env`, no shell variable.
- **C (correct).** `Settings` has `llm_base_url: str = Field(min_length=1)` with no default, so pydantic raises `ValidationError` inside `load_config`, at startup. Example: `python -c "from rag_agent.config import load_config; load_config()"` fails right away.
- A: Wrong. The code has no default URL. `.env.example` is only a template.
- B: Wrong. This is the failure the design avoids. Errors would be deferred to the first request without a startup check.
- D: Wrong. `llm_model` has a default, but `llm_base_url` does not, so the missing URL still fails.

## Q3. Empty `LLM_BASE_URL=""`.
- **A (correct).** An empty string is a valid `str`. The `min_length=1` constraint is what rejects it. `test_empty_required_env_fails_fast` exists because someone could remove the constraint and the missing-value test would still pass. Example: `LLM_BASE_URL=` in `.env` would otherwise start the app with an empty endpoint.
- B: Wrong. pydantic raises a validation error. It does not crash the process.
- C: Wrong. `llm_model` is a separate field with its own default.
- D: Wrong. `.env` values are read as written, empty values included. That is why the empty case needs its own test.

## Q4. `env_file=None` in tests.
- **D (correct).** `load_config` reads `.env` by default (`env_file: str | None = ".env"`). If a developer has a real `.env` with a working URL, a test expecting the "missing" error would pass or fail depending on their machine. Passing `None` makes the test read only the environment it sets with `monkeypatch`.
- A: Wrong. The YAML path is passed explicitly in every test (`_write_tunables` writes into `tmp_path`).
- B: Wrong. The speed of YAML parsing is not the point.
- C: Wrong. `.env` is still read in production, because the default is `".env"`. The parameter exists only so tests can switch it off.

## Q5. Pinned llama.cpp tag.
- **A (correct).** `ghcr.io/ggml-org/llama.cpp:server-b11718` names one build. `latest` moves whenever upstream publishes, so the same Dockerfile can build a different server on a different day. This is decision D2 in the spec.
- B: Wrong. No such Docker Hub rule exists. The reason is reproducibility, not policy.
- C: Wrong. The tag has no effect on image size.
- D: Wrong. Docker builds a `FROM latest` line without complaint. The pin is about reproducibility.

## Q6. Copy instead of re-download.
- **C (correct).** The Ollama blob is the same bytes as the model Ollama already has, so no second download is needed. The `sha256-<hash>` name in the blob path gives the expected checksum, and `sha256sum` on the copy verifies it. Example: a mismatch means the copy is corrupt.
- A: Wrong. `cp` copies the same bytes. A different file would fail the checksum.
- B: Wrong. Nothing in the script suggests encryption. The check compares plain hashes, and Ollama blobs are GGUF files.
- D: Wrong. The Dockerfile still needs `COPY`, because `models/` is what gets baked into the image.

## Q7. Checksum mismatch.
- **B (correct).** The script runs `set -euo pipefail` and has an explicit `exit 1` after the mismatch message. The bad file is not deleted, so a careless next step (like `docker build`) could use it. The build should only go ahead when the script exits 0.
- A: Wrong. The script never deletes `DEST`. It only exits with an error, and the build does not fall back to the Ollama blob.
- C: Wrong. There is no retry loop.
- D: Wrong. The check exits 1, so `&&` chains and `make` stop.

## Q8. Two bind addresses.
- **C (correct).** Inside the container, `127.0.0.1` means only the container itself. Docker's port forwarding arrives on the container's network interface, so the server must listen on `0.0.0.0`. On the host, the publish `127.0.0.1:8081:8080` means only the dev PC can reach it.
- A: Wrong. `0.0.0.0` means all interfaces. `127.0.0.1` means loopback only.
- B: Wrong. Compose does not require it. The `llm` service also publishes on `127.0.0.1`, so the rule is not Phoenix-only.
- D: Wrong. The host-side `127.0.0.1` is what keeps the port off the network. The container-side `0.0.0.0` only means "all interfaces inside the container".

## Q9. `.env.example` URL vs the published port.
- **D (correct).** `.env.example` says `http://localhost:8080/v1` is the local llm container, but `docker-compose.yml` publishes `127.0.0.1:${LLM_HOST_PORT:-8081}:8080`. With defaults, the host's 8080 is Jenkins on the dev PC, so the app's calls go to the wrong service. Example: `curl localhost:8080/v1/chat/completions` from the host does not reach the llm container. Use `localhost:8081` on the host, or set `LLM_HOST_PORT=8080` only if Jenkins is stopped.
- A: Wrong. The host port is what the host uses. The container's internal 8080 is not reachable from the host on 8080 unless it is published there.
- B: Wrong. Nothing in the code cross-checks `.env` against the compose file. Only `min_length=1` is checked.
- C: Wrong. Compose does not read or edit `.env` for this purpose.

## Q10. Port 8081.
- **C (correct).** The comment in `docker-compose.yml` says 8080 is taken by Jenkins on the dev PC. The container still listens on 8080 internally, and `LLM_HOST_PORT` overrides the host port.
- A: Wrong. The server does not care which host port is used. Port 8080 is a host-side clash, not a server limit.
- B: Wrong. The healthcheck uses `localhost:8080` inside the container, not the host port.
- D: Wrong. Docker does not reserve 8080. The code gives Jenkins as the reason.

## Q11. gitleaks as a pre-commit hook.
- **D (correct).** Once a secret is committed, it stays in history even after deletion, so the key must be rotated. Stopping it before the commit is much cheaper. Example: an API key committed on Monday and removed on Tuesday is still in `git log`.
- A: Wrong. Formatting is done by ruff-format, not gitleaks.
- B: Wrong. Nothing in GitHub or the code requires it. It is a local choice.
- C: Wrong. CI runs ruff, mypy and pytest. gitleaks does not replace the test job.

## Q12. `uv sync --locked` in CI.
- **A (correct).** `--locked` makes `uv` fail if `uv.lock` does not match `pyproject.toml`. The tests then always run against the dependencies that were committed and reviewed. Example: someone adds `httpx` to `pyproject.toml` but forgets `uv lock`, so CI stops at the install step.
- B: Wrong. `--locked` installs exactly what the lock says. Upgrading is a separate, explicit step.
- C: Wrong. The flag does the opposite: it uses the lock and refuses to re-resolve it.
- D: Wrong. `ci.yml` does not run gitleaks at all. See the teaching note.

## Teaching note (tutor only)
`ci.yml` does not run gitleaks. The check exists only as a local pre-commit hook, so a contributor who skips `uv run pre-commit install` gets no secret scan in CI. Use this as a follow-up question after grading, for example: "What would you add to `ci.yml` to close that gap?"

Second open issue for the tutor: `.env.example` gives `http://localhost:8080/v1` as the local llm URL, but the compose default host port is 8081 (Q9). Ask Mahdi how he would fix the mismatch and whether the fix belongs in the spec or the code. Do not edit the files yourself.
