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


def test_overlap_must_be_smaller_than_chunk_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:8080/v1")
    text = TUNABLES_YAML.replace("chunk_overlap_chars: 100", "chunk_overlap_chars: 800")

    with pytest.raises(ValidationError):
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
