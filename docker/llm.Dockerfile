# Local OpenAI-compatible model server. The model is baked in so the container runs offline.
# llama.cpp server build pinned by number (spec B1, D2). Never use :latest.
FROM ghcr.io/ggml-org/llama.cpp:server-b11718

# models/ is gitignored. scripts/export_model.sh fills it from the local Ollama download.
COPY models/qwen2.5-0.5b-instruct-q4_k_m.gguf /models/qwen2.5-0.5b-instruct-q4_k_m.gguf

# Bind to all interfaces so other containers and the host can reach the server.
CMD ["-m", "/models/qwen2.5-0.5b-instruct-q4_k_m.gguf", "-c", "4096", "--jinja", "--host", "0.0.0.0", "--port", "8080"]
EXPOSE 8080
