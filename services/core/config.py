"""Load settings from env and YAML config files."""
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (TimescaleDB/PostgreSQL)
    database_url: str = Field(
        default="postgresql+asyncpg://macro:macro@localhost:5432/macroedge",
        description="Async PostgreSQL URL",
    )

    # Sync URL for migrations (psycopg2-style)
    database_url_sync: str = Field(
        default="postgresql://macro:macro@localhost:5432/macroedge",
        description="Sync URL for migrations",
    )

    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Paths
    config_dir: Path = Field(default_factory=lambda: Path("config"))

    # FRED API (ingestion)
    fred_api_key: str = Field(default="", description="FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html")

    def get_indicators_config(self) -> dict[str, Any]:
        p = self.config_dir / "indicators.yaml"
        if not p.exists():
            p = self.config_dir / "indicators.example.yaml"
        return _load_yaml(p)

    def get_indices_config(self) -> dict[str, Any]:
        p = self.config_dir / "indices.yaml"
        if not p.exists():
            p = self.config_dir / "indices.example.yaml"
        return _load_yaml(p)

    def get_bias_engine_config(self) -> dict[str, Any]:
        p = self.config_dir / "bias_engine.yaml"
        if not p.exists():
            p = self.config_dir / "bias_engine.example.yaml"
        return _load_yaml(p)


def get_settings() -> Settings:
    return Settings()
