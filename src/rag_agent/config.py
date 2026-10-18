"""Application configuration.

Two sources, by purpose:
- ``config.yaml`` holds tunables that are the same in every environment.
- Environment variables (or ``.env``) hold secrets and environment-specific values.

Both are validated when loaded, so a missing required value stops the app at startup.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Tunables(BaseModel):
    """Values from ``config.yaml``."""

    llm_timeout_seconds: float = Field(gt=0)


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
