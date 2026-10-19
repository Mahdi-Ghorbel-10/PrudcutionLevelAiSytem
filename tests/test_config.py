from pathlib import Path

import pytest
from pydantic import ValidationError

from rag_agent.config import load_config

TUNABLES_YAML = """\
llm_timeout_seconds: 12
ingestion:
  chunk_size_chars: 800
  chunk_overlap_chars: 100
  embed_with_heading: true
  chroma_path: data/chroma
  collection_name: chunks
  embedding_model: BAAI/bge-small-en-v1.5
  embed_batch_size: 32
retrieval:
  mode: hybrid_rerank
  dense_top_k: 20
  bm25_top_k: 20
  rrf_k: 60
  fused_top_k: 10
  rerank_top_k: 4
  rerank_model: cross-encoder/ms-marco-MiniLM-L-6-v2
"""


def _write_tunables(tmp_path: Path, text: str = TUNABLES_YAML) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_yaml_tunables_and_env_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = load_config(_write_tunables(tmp_path), env_file=None)

    assert config.settings.llm_base_url == "http://localhost:8080/v1"
    assert config.settings.llm_model == "local"
    assert config.tunables.llm_timeout_seconds == 12
    assert config.tunables.ingestion.chunk_size_chars == 800
    assert config.tunables.ingestion.chunk_overlap_chars == 100
    assert config.tunables.ingestion.embed_with_heading is True
    assert config.tunables.ingestion.chroma_path == Path("data/chroma")
    assert config.tunables.ingestion.collection_name == "chunks"
    assert config.tunables.ingestion.embedding_model == "BAAI/bge-small-en-v1.5"


def test_overlap_must_be_smaller_than_chunk_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    text = TUNABLES_YAML.replace("chunk_overlap_chars: 100", "chunk_overlap_chars: 800")

    with pytest.raises(ValidationError):
        load_config(_write_tunables(tmp_path, text), env_file=None)


def test_retrieval_defaults_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")

    config = load_config(_write_tunables(tmp_path), env_file=None)

    retrieval = config.tunables.retrieval
    assert retrieval.mode == "hybrid_rerank"
    assert (retrieval.dense_top_k, retrieval.bm25_top_k) == (20, 20)
    assert (retrieval.fused_top_k, retrieval.rerank_top_k) == (10, 4)
    assert retrieval.rrf_k == 60


def test_unknown_retrieval_mode_fails_at_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    text = TUNABLES_YAML.replace("mode: hybrid_rerank", "mode: bogus")

    with pytest.raises(ValidationError, match="hybrid_rerank"):
        load_config(_write_tunables(tmp_path, text), env_file=None)


def test_fused_top_k_larger_than_the_candidates_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    text = TUNABLES_YAML.replace("fused_top_k: 10", "fused_top_k: 41")

    with pytest.raises(ValidationError, match="fused_top_k must not exceed"):
        load_config(_write_tunables(tmp_path, text), env_file=None)


def test_missing_required_env_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    with pytest.raises(ValidationError):
        load_config(_write_tunables(tmp_path), env_file=None)


def test_empty_required_env_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "")

    with pytest.raises(ValidationError):
        load_config(_write_tunables(tmp_path), env_file=None)


def test_non_positive_timeout_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    text = TUNABLES_YAML.replace("llm_timeout_seconds: 12", "llm_timeout_seconds: 0")

    with pytest.raises(ValidationError):
        load_config(_write_tunables(tmp_path, text), env_file=None)
