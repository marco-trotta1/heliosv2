from __future__ import annotations

import logging
from dataclasses import dataclass, field

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
