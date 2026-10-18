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
- [ ] C. So a developer's real `.env` cannot change the test results.
- [ ] D. So `.env` is always ignored in production.

### Q5. The Dockerfile pins `server-b11718` and forbids `:latest`. Why?

- [ ] A. A rebuild next month should give the same server, while `latest` can change under the same name.
- [ ] B. Docker Hub does not allow `latest` tags for public images.
- [ ] C. Pinned tags produce smaller images.
- [ ] D. llama.cpp accepts the `--jinja` flag only in numbered builds.

### Q6. `scripts/export_model.sh` copies the Ollama blob instead of downloading the model again. What does this buy?

- [ ] A. The copy is a different, smaller model file than the one Ollama holds.
- [ ] B. It avoids a second download, and the sha256 check proves the copy is byte-identical.
- [ ] C. Ollama blobs are encrypted, so only a copy can be read by llama.cpp.
- [ ] D. The Docker build can then skip the `COPY` step.

### Q7. The sha256 check in `export_model.sh` fails. What is the state of `models/` afterwards, and what should happen to the build?

- [ ] A. The script deletes the copy, and the build still works from the Ollama blob.
- [ ] B. The script exits with an error, the bad copy stays in `models/`, and the build must not use it.
- [ ] C. The script retries the copy until the hashes match.
- [ ] D. The script prints a warning and exits 0, so the build continues.

### Q8. `docker-compose.yml` publishes the port as `127.0.0.1:8081:8080`, but the server inside the container binds to `0.0.0.0`. Why both?

- [ ] A. `0.0.0.0` and `127.0.0.1` are the same, so the two lines are redundant.
- [ ] B. Inside the container, `0.0.0.0` lets Docker's port forwarding reach the server. On the host, `127.0.0.1` keeps it off the local network.
- [ ] C. Compose requires `0.0.0.0` in the `CMD`, and `127.0.0.1` is only for Phoenix.
- [ ] D. `0.0.0.0` exposes the host to the internet, so compose must override it.

### Q9. Someone removes `--host 0.0.0.0` from the `CMD`. What breaks?

- [ ] A. `curl localhost:8081` from the host fails, while the in-container healthcheck still passes.
- [ ] B. The model fails to load because it cannot read the GGUF file.
- [ ] C. The healthcheck fails, and compose refuses to start the stack.
- [ ] D. Nothing changes, because llama.cpp already listens on all interfaces by default.

### Q10. The host port is `${LLM_HOST_PORT:-8081}`, not `8080`. Why?

- [ ] A. The llama.cpp server accepts connections only on port 8081 from outside.
- [ ] B. The healthcheck requires port 8081.
- [ ] C. Port 8080 is already used on the dev PC by Jenkins, so the default moved and stays overridable.
- [ ] D. Docker reserves port 8080 for its own API.

### Q11. Why does gitleaks run as a pre-commit hook?

- [ ] A. It formats the code before review.
- [ ] B. A secret that reaches a commit stays in git history even after it is deleted, so it is cheaper to stop it before the commit.
- [ ] C. GitHub requires it before any push to `Dev`.
- [ ] D. It replaces the unit test job in CI.
