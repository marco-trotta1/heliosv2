from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient

from helios.api.main import create_app
from helios.api.runtime import AppRuntime
from helios.config import get_settings
from helios.database.db import init_db, reset_engine
from helios.models.moisture_model import clear_model_cache
import helios.schemas.outputs as output_schemas
from helios.utils.openet import clear_openet_cache


class PickledFakeModel:
    def predict(self, matrix: Any) -> np.ndarray:
        row_count = len(matrix.index) if hasattr(matrix, "index") else 1
        return np.array([[0.24, 0.16, 0.13] for _ in range(row_count)])


@pytest.fixture()
def temp_settings_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    database_path = tmp_path / "data" / "helios-test.db"
    model_path = tmp_path / "artifacts" / "moisture_model.pkl"
    metadata_path = tmp_path / "artifacts" / "model_metadata.json"

    monkeypatch.setenv("HELIOS_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("HELIOS_MODEL_PATH", str(model_path))
    monkeypatch.setenv("HELIOS_METADATA_PATH", str(metadata_path))
    monkeypatch.setenv("HELIOS_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HELIOS_RATE_LIMIT_MAX_REQUESTS", "100")
    monkeypatch.setenv("HELIOS_CORS_ALLOW_ORIGINS", "https://example-pages.test")

    get_settings.cache_clear()
    clear_model_cache()
    clear_openet_cache()
    reset_engine()

    yield {
        "database_path": database_path,
        "model_path": model_path,
        "metadata_path": metadata_path,
    }

    reset_engine()
    clear_model_cache()
    clear_openet_cache()
    get_settings.cache_clear()


@pytest.fixture()
def prediction_payload() -> dict[str, Any]:
    timestamp = datetime(2026, 3, 17, 18, 0, tzinfo=timezone.utc)
    return {
        "field_id": "field-001",
        "farm_id": "farm-001",
        "forecast_horizon_hours": 72,
        "weather": {
            "temperature_f": 87.8,
            "humidity_pct": 38.0,
            "wind_mph": 8.5,
            "precipitation_in": 0.0,
            "solar_radiation_mj_m2": 24.0,
            "forecast_horizon_hours": 72,
        },
        "irrigation_system": {
            "irrigation_type": "pivot",
            "pump_capacity_in_per_hour": 0.236,
            "water_rights_schedule": ["tonight", "tomorrow_morning"],
            "energy_price_window": ["tonight"],
        },
        "soil_moisture_readings": [
            {
                "timestamp": (timestamp - timedelta(hours=18)).isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-a",
                "volumetric_water_content": 0.24,
            },
            {
                "timestamp": (timestamp - timedelta(hours=12)).isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-b",
                "volumetric_water_content": 0.28,
            },
            {
                "timestamp": (timestamp - timedelta(hours=9)).isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-a",
                "volumetric_water_content": 0.22,
            },
            {
                "timestamp": (timestamp - timedelta(hours=6)).isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-b",
                "volumetric_water_content": 0.25,
            },
            {
                "timestamp": (timestamp - timedelta(hours=3)).isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-a",
                "volumetric_water_content": 0.20,
            },
            {
                "timestamp": timestamp.isoformat(),
                "field_id": "field-001",
                "sensor_id": "sensor-b",
                "volumetric_water_content": 0.23,
            },
        ],
        "soil_properties": {
            "soil_texture": "loam",
            "infiltration_rate_in_per_hour": 0.472,
            "slope_pct": 2.5,
            "drainage_class": "moderate",
        },
        "crop": {
            "crop_type": "corn",
            "growth_stage": "flowering",
        },
        "operational": {
            "max_irrigation_volume_in": 0.709,
            "field_area_acres": 59.3,
            "budget_dollars": 2800.0,
        },
        "location_lat": 43.615,
        "location_lon": -116.202,
        "recent_irrigation_events": [
            {
                "timestamp": (timestamp - timedelta(hours=24)).isoformat(),
                "applied_in": 0.315,
            }
        ],
    }


@pytest.fixture
def known_inference_row():
    """A minimal valid inference input for sanity-checking model output range."""
    return {
        "temperature_f": 82.0,
        "humidity_pct": 35.0,
        "wind_mph": 8.0,
        "precipitation_in": 0.0,
        "solar_radiation_mj_m2": 22.0,
        "volumetric_water_content_lag1": 0.28,
        "volumetric_water_content_lag2": 0.30,
        "current_vwc": 0.26,
        "crop_type": "potato",
        "growth_stage": "tuber_bulking",
        "soil_texture": "silt_loam",
        "irrigation_type": "pivot",
    }


@pytest.fixture()
def feedback_payload() -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "farm_id": "farm-001",
        "timestamp": timestamp.isoformat(),
        "crop_type": "corn",
        "soil_texture": "loam",
        "irrigation_type": "pivot",
        "growth_stage": "flowering",
        "recommendation_type": "irrigation",
        "recommendation_value": "12.5",
        "outcome": "SUCCESS",
        "yield_delta": 4.0,
        "notes": "Looked good.",
        "location_lat": 43.615,
        "location_lon": -116.202,
    }


def write_fake_model_artifacts(model_path: Path, metadata_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(PickledFakeModel(), model_path)
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": [],
                "cv_rmse_mean": 0.11,
            }
        )
    )


def make_prediction_response() -> output_schemas.PredictionResponse:
    return output_schemas.PredictionResponse(
        decision="water",
        recommended_amount_in=0.492,
        timing_window="tonight",
        confidence_score=0.74,
        explanation=output_schemas.RecommendationExplanation(
            predicted_moisture_48h=0.16,
            stress_probability=0.82,
            drivers=["low soil moisture", "limited forecast precipitation"],
            driving_zone="sensor-a",
            zone_moisture_summary={"sensor-a": 0.20, "sensor-b": 0.23},
            high_variability_flag=False,
        ),
        predicted_moisture=output_schemas.MoistureForecast(
            moisture_24h=0.2,
            moisture_48h=0.16,
            moisture_72h=0.13,
        ),
        regional_insights=output_schemas.RegionalInsights(
            success_rate=0.78,
            avg_yield_delta=4.0,
            total_samples=6,
            weighted_samples=4.2,
            comparable_samples=4,
            radius_miles=31.07,
        ),
        recommendation_adjustment=output_schemas.RecommendationAdjustment(
            base_recommendation_in=0.465,
            adjusted_recommendation_in=0.492,
            adjustment_factor=1.06,
            reason="Comparable nearby feedback was consistently positive, so the recommendation was modestly reinforced.",
        ),
    )


@pytest.fixture()
def prediction_response() -> output_schemas.PredictionResponse:
    return make_prediction_response()


@pytest.fixture()
def app_factory(
    temp_settings_env: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., TestClient]:
    def _build(
        *,
        recommendation_service: Any | None = None,
        database_ready: bool = True,
        startup_issues: list[str] | None = None,
    ) -> TestClient:
        import helios.api.main as main_module

        def fake_build_runtime(settings):
            if database_ready:
                init_db()
            return AppRuntime(
                settings=settings,
                recommendation_service=recommendation_service,
                database_ready=database_ready,
                startup_issues=list(startup_issues or []),
            )

        monkeypatch.setattr(main_module, "build_runtime", fake_build_runtime)
        app = create_app(get_settings())
        return TestClient(app)

    return _build
