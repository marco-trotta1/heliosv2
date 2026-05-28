from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from helios.data.feature_engineering import build_expected_feature_columns
from helios.api.rate_limit import InMemoryRateLimiter, RateLimitPolicy
from helios.config import Settings
from helios.database.db import init_db
from helios.services.recommendation_service import RecommendationService


logger = logging.getLogger(__name__)


@dataclass
class AppRuntime:
    settings: Settings
    recommendation_service: RecommendationService | None = None
    database_ready: bool = False
    startup_issues: list[str] = field(default_factory=list)
    rate_limiter: InMemoryRateLimiter | None = None

    @property
    def ready(self) -> bool:
        return self.database_ready and self.recommendation_service is not None


class ModelFeatureSchemaMismatch(RuntimeError):
    pass


def validate_model_feature_schema(metadata_path: Path) -> None:
    metadata = json.loads(metadata_path.read_text())
    metadata_columns = metadata.get("feature_columns")
    if not isinstance(metadata_columns, list) or not all(isinstance(column, str) for column in metadata_columns):
        raise ModelFeatureSchemaMismatch("Model metadata feature_columns must be a list of strings.")

    builder_columns = build_expected_feature_columns()
    if metadata_columns == builder_columns:
        return

    metadata_set = set(metadata_columns)
    builder_set = set(builder_columns)
    missing_columns = [column for column in builder_columns if column not in metadata_set]
    extra_columns = [column for column in metadata_columns if column not in builder_set]
    raise ModelFeatureSchemaMismatch(
        "Model feature schema mismatch.\n"
        f"metadata feature columns: {metadata_columns}\n"
        f"feature builder feature columns: {builder_columns}\n"
        f"missing columns: {missing_columns}\n"
        f"extra columns: {extra_columns}"
    )


def build_runtime(settings: Settings) -> AppRuntime:
    runtime = AppRuntime(
        settings=settings,
        rate_limiter=InMemoryRateLimiter(
            RateLimitPolicy(
                window_seconds=settings.rate_limit_window_seconds,
                max_requests=settings.rate_limit_max_requests,
            )
        ),
    )

    try:
        init_db()
        runtime.database_ready = True
    except Exception:
        logger.exception("Failed to initialize the Helios database")
        runtime.startup_issues.append("Database initialization failed.")

    try:
        validate_model_feature_schema(settings.metadata_path)
        runtime.recommendation_service = RecommendationService.from_artifacts(
            model_path=settings.model_path,
            metadata_path=settings.metadata_path,
            validation_mode=settings.validation_mode,
        )
    except FileNotFoundError:
        logger.warning(
            "Model artifacts were not found at startup",
            extra={
                "model_path": str(settings.model_path),
                "metadata_path": str(settings.metadata_path),
            },
        )
        runtime.startup_issues.append("Model artifacts are missing. Train the model before using live API mode.")
    except ModelFeatureSchemaMismatch as exc:
        logger.error("Model feature schema validation failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    except Exception:
        logger.exception("Failed to load Helios model artifacts")
        runtime.startup_issues.append("Model artifacts could not be loaded.")

    if runtime.ready:
        logger.info("Helios API runtime is ready")
    else:
        logger.warning("Helios API runtime started in degraded mode", extra={"issues": runtime.startup_issues})

    if settings.strict_model_startup and runtime.recommendation_service is None:
        raise RuntimeError("HELIOS_STRICT_MODEL_STARTUP is enabled and model artifacts are unavailable.")

    return runtime
