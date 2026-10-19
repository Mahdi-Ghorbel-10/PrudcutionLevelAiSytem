from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

from rag_agent import cli
from rag_agent.config import IngestionTunables
from rag_agent.retrieval.embedder import Embedder

CONFIG_YAML = """\
llm_timeout_seconds: 12
ingestion:
  chunk_size_chars: 800
  chunk_overlap_chars: 100
  embed_with_heading: true
  chroma_path: chroma
  collection_name: chunks
  embedding_model: unused
  embed_batch_size: 8
retrieval:
  mode: hybrid
  dense_top_k: 20
  bm25_top_k: 20
  rrf_k: 60
  fused_top_k: 10
  rerank_top_k: 4
  rerank_model: unused
"""


class FakeEncoder:
    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
    ) -> Any:
        return np.ones((len(sentences), 3))


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "leave.md").write_text("# Leave\n\nTwelve weeks of leave.\n", encoding="utf-8")

    def fake_embedder(ingestion: IngestionTunables) -> Embedder:
        return Embedder("unused", batch_size=ingestion.embed_batch_size, model=FakeEncoder())

    monkeypatch.setattr(cli, "_make_embedder", fake_embedder)
    return docs


def test_ingest_prints_counts_and_second_run_adds_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = _setup(tmp_path, monkeypatch)
    runner = CliRunner()

    first = runner.invoke(cli.app, ["ingest", str(docs)])
    second = runner.invoke(cli.app, ["ingest", str(docs)])

    assert first.exit_code == 0, first.output
    assert "chunks added: 1" in first.output
    assert "chunks added: 0" in second.output
    assert "chunks skipped: 1" in second.output


def test_search_ranks_the_keyword_match_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = _setup(tmp_path, monkeypatch)
    (docs / "expenses.txt").write_text("Taxi fares need a copperkettle code.", encoding="utf-8")
    runner = CliRunner()
    runner.invoke(cli.app, ["ingest", str(docs)])

    result = runner.invoke(cli.app, ["search", "copperkettle"])

    assert result.exit_code == 0, result.output
    first_line = result.output.splitlines()[0]
    assert first_line.startswith("1. score")
    assert "expenses.txt" in first_line
    assert result.output.rstrip().endswith("degraded: none")


def test_ingest_rejects_a_missing_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(tmp_path, monkeypatch)

    result = CliRunner().invoke(cli.app, ["ingest", str(tmp_path / "nope")])

    assert result.exit_code != 0
