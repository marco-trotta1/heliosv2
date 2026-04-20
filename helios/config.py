from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    database_path: Path
    model_path: Path
    metadata_path: Path
    cors_allowed_origins: tuple[str, ...]
    rate_limit_window_seconds: int
    rate_limit_max_requests: int
    strict_model_startup: bool
    log_level: str
    api_key: str
    validation_mode: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name="Helios",
        app_version="0.2.0",
        database_path=Path(os.getenv("HELIOS_DATABASE_PATH", "data/helios.db")),
        model_path=Path(os.getenv("HELIOS_MODEL_PATH", "artifacts/moisture_model.pkl")),
        metadata_path=Path(os.getenv("HELIOS_METADATA_PATH", "artifacts/model_metadata.json")),
        cors_allowed_origins=_env_csv("HELIOS_CORS_ALLOW_ORIGINS", ("http://localhost", "http://localhost:5173")),
        rate_limit_window_seconds=_env_int("HELIOS_RATE_LIMIT_WINDOW_SECONDS", 60),
        rate_limit_max_requests=_env_int("HELIOS_RATE_LIMIT_MAX_REQUESTS", 60),
        strict_model_startup=_env_bool("HELIOS_STRICT_MODEL_STARTUP", False),
        log_level=os.getenv("HELIOS_LOG_LEVEL", "INFO").upper(),
        api_key=os.getenv("HELIOS_API_KEY", ""),
        validation_mode=_env_bool("HELIOS_VALIDATION_MODE", False),
    )
