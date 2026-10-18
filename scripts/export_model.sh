#!/usr/bin/env bash
# Copy the Qwen GGUF that Ollama already downloaded into models/, so the llm image can bake it in.
# No second download. The copy is checked against the hash in Ollama's blob name.
set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M}"
DEST="${DEST:-models/qwen2.5-0.5b-instruct-q4_k_m.gguf}"

cd "$(dirname "$0")/.."

blob="$(ollama show --modelfile "$OLLAMA_MODEL" | sed -n 's/^FROM //p' | head -n 1)"
if [ -z "$blob" ]; then
  echo "error: no FROM line for $OLLAMA_MODEL. Run 'ollama list' to check the model name." >&2
  exit 1
fi
if [ ! -r "$blob" ]; then
  echo "error: cannot read $blob. Run with sudo, or add your user to the group that owns it." >&2
  exit 1
fi

# Ollama names blobs sha256-<hash>. The hash is the expected checksum of the file.
expected="$(basename "$blob" | sed -n 's/^sha256-//p')"

mkdir -p "$(dirname "$DEST")"
cp "$blob" "$DEST"

actual="$(sha256sum "$DEST" | cut -d ' ' -f 1)"
if [ "$actual" != "$expected" ]; then
  echo "error: checksum mismatch for $DEST (expected $expected, got $actual)" >&2
  exit 1
fi

echo "ok: $DEST (sha256 $actual)"
