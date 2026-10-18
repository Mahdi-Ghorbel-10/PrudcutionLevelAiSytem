# Quiz: B1 Scaffolding (Phase 1)

Merged in PR #1 (`b562f73` on `Dev`). Spec: `specs/B1-scaffolding.md`.

How to answer: tick one box per question. Then tell the tutor "my answers are ready" in a tutor session (`claude --agent tutor`). Do not write answers anywhere else.

Mix: multiple choice, "what breaks if", and "why was this chosen". Each question is about the merged code.

---

### Q1. Why is `llm_timeout_seconds` in `config.yaml`, while `LLM_BASE_URL` is in `.env`?

- [ ] A. YAML loads faster than environment variables.
- [ ] B. The timeout is the same in every environment, while the URL and secrets change per machine.
- [ ] C. pydantic can only validate environment variables, not YAML.
- [ ] D. Secrets must go in YAML so git can ignore them.

### Q2. A fresh clone has no `.env`, and `LLM_BASE_URL` is not set in the shell. What happens when the app starts?

- [ ] A. It falls back to `http://localhost:8080/v1` and runs.
- [ ] B. It starts, and the first LLM call fails with a timeout.
- [ ] C. `load_config` raises `ValidationError` before any request is served.
- [ ] D. It uses the default `llm_model="local"` and skips the URL.

### Q3. The tests include one for an empty `LLM_BASE_URL=""`, separate from the missing-value test. What does the empty-value test protect against?

- [ ] A. An empty string passes a plain `str` check, so the app would start with no endpoint.
- [ ] B. Empty values make pydantic crash with a segmentation fault.
- [ ] C. An empty string is read as the default model name `local`.
- [ ] D. Empty values are never read from `.env`, so a missing value is never reported.

### Q4. `load_config` takes `env_file` as a parameter, and the tests pass `env_file=None`. Why?

- [ ] A. Otherwise pytest cannot find `config.yaml`.
- [ ] B. It makes the tests faster by skipping YAML parsing.
- [ ] C. So `.env` is always ignored in production.
- [ ] D. So a developer's real `.env` cannot change the test results.

### Q5. The Dockerfile pins `server-b11718` and forbids `:latest`. Why?

- [ ] A. A rebuild next month should give the same server, while `latest` can change under the same name.
- [ ] B. Docker Hub does not allow `latest` tags for public images.
- [ ] C. Pinned tags produce smaller images.
- [ ] D. Docker refuses to build a `FROM` line that uses `latest`.

### Q6. `scripts/export_model.sh` copies the Ollama blob instead of downloading the model again. What does this buy?

- [ ] A. The copy is a different, smaller model file than the one Ollama holds.
- [ ] B. Ollama blobs are encrypted, so only a copy can be read by llama.cpp.
- [ ] C. It avoids a second download, and the sha256 check proves the copy matches the blob's hash.
- [ ] D. The Docker build can then skip the `COPY` step.

### Q7. The sha256 check in `export_model.sh` fails. What state is `models/` in afterwards, and what should happen to the build?

- [ ] A. The script deletes the copy, and the build still works from the Ollama blob.
- [ ] B. The script exits with an error and leaves the bad copy in `models/`. A build that runs after it must not use that file.
- [ ] C. The script retries the copy until the hashes match.
- [ ] D. The script prints a warning and exits 0, so the build continues.

### Q8. `docker-compose.yml` publishes the port as `127.0.0.1:…:8080`, and the `CMD` makes the server bind to `0.0.0.0`. Why both?

- [ ] A. `0.0.0.0` and `127.0.0.1` are the same address, so the two settings are redundant.
- [ ] B. Compose requires `0.0.0.0` in every `CMD`, and `127.0.0.1` is only for Phoenix.
- [ ] C. Inside the container, the server listens on all interfaces so Docker's port forwarding can reach it. On the host, the published port is bound to loopback, so the LAN cannot reach it.
- [ ] D. `0.0.0.0` exposes the host to the internet, so compose must override it.

### Q9. `.env.example` says the local llm container is at `http://localhost:8080/v1`. You copy that value into `.env`, start the stack with default settings, and run the app on the host. What happens?

- [ ] A. The request reaches the llm container, because the container listens on 8080 and the host port does not matter.
- [ ] B. The app refuses to start, because `.env` must match the compose file.
- [ ] C. Compose rewrites the URL in `.env` to 8081 while the stack is up.
- [ ] D. The request does not reach the llm container. The stack publishes it on host port 8081 by default, and host port 8080 belongs to another service.

### Q10. The host port is `${LLM_HOST_PORT:-8081}`, not `8080`. Why?

- [ ] A. The llama.cpp server accepts connections only on port 8081 from outside.
- [ ] B. The healthcheck requires port 8081.
- [ ] C. Port 8080 is already used on the dev PC by Jenkins, so the default moved and stays overridable.
- [ ] D. Docker reserves port 8080 for its own API.

### Q11. Why does gitleaks run as a pre-commit hook?

- [ ] A. It formats the code before review.
- [ ] B. GitHub requires it before any push to `Dev`.
- [ ] C. It replaces the unit test job in CI.
- [ ] D. A secret that reaches a commit stays in git history even after it is deleted, so it is cheaper to stop it before the commit.

### Q12. CI runs `uv sync --locked`. What does the `--locked` flag guard against?

- [ ] A. A pull request that changes `pyproject.toml` without updating `uv.lock` fails before the tests run.
- [ ] B. CI upgrades every dependency to the newest release before testing.
- [ ] C. CI ignores `uv.lock` and resolves versions fresh on each run.
- [ ] D. CI runs gitleaks before the lint step.
