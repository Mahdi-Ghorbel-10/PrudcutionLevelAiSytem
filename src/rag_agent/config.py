"""Application configuration.

Two sources, by purpose:
- ``config.yaml`` holds tunables that are the same in every environment.
- Environment variables (or ``.env``) hold secrets and environment-specific values.

Both are validated when loaded, so a missing required value stops the app at startup.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionTunables(BaseModel):
    """The ``ingestion`` section of ``config.yaml``."""

    chunk_size_chars: int = Field(gt=0)
    chunk_overlap_chars: int = Field(ge=0)
    embed_with_heading: bool
    chroma_path: Path
    collection_name: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    embed_batch_size: int = Field(gt=0)

    @model_validator(mode="after")
    def _overlap_is_smaller_than_chunk(self) -> "IngestionTunables":
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")
        return self


RetrievalMode = Literal["dense", "bm25", "hybrid", "hybrid_rerank"]


class RetrievalTunables(BaseModel):
    """The ``retrieval`` section of ``config.yaml``. ``mode`` selects which stages run."""

    mode: RetrievalMode
    dense_top_k: int = Field(gt=0)
    bm25_top_k: int = Field(gt=0)
    rrf_k: int = Field(gt=0)
    fused_top_k: int = Field(gt=0)
    rerank_top_k: int = Field(gt=0)
    rerank_model: str = Field(min_length=1)

    @model_validator(mode="after")
    def _fused_fits_the_candidates(self) -> "RetrievalTunables":
        if self.fused_top_k > self.dense_top_k + self.bm25_top_k:
            raise ValueError("fused_top_k must not exceed dense_top_k + bm25_top_k")
        return self


class Tunables(BaseModel):
    """Values from ``config.yaml``."""

    llm_timeout_seconds: float = Field(gt=0)
    ingestion: IngestionTunables
    retrieval: RetrievalTunables


class Settings(BaseSettings):
    """Values from environment variables or ``.env``."""

    model_config = SettingsConfigDict(extra="ignore")

    llm_base_url: str = Field(min_length=1)
    llm_model: str = "local"


class AppConfig(BaseModel):
    """Everything the app needs at startup."""

    settings: Settings
    tunables: Tunables


def load_tunables(path: Path) -> Tunables:
    """Read and validate the YAML tunables file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Tunables.model_validate(data)


def load_config(
    config_path: Path = Path("config.yaml"),
    env_file: str | None = ".env",
) -> AppConfig:
    """Load and validate all configuration. Raises ``ValidationError`` when a value is missing."""
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    return AppConfig(settings=settings, tunables=load_tunables(config_path))
