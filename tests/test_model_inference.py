from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from helios.config import get_settings
from helios.data.feature_engineering import build_inference_features
from helios.services.recommendation_service import RecommendationService


def _build_known_feature_frame(known_inference_row: dict[str, float | str]) -> pd.DataFrame:
    current_vwc = float(known_inference_row["current_vwc"])
    lag_1 = float(known_inference_row["volumetric_water_content_lag1"])
    lag_2 = float(known_inference_row["volumetric_water_content_lag2"])
    return pd.DataFrame(
        [
            {
                "field_id": "known-field",
                "primary_sensor_id": "sensor-a",
                "forecast_horizon_hours": 48,
                "temperature_f": known_inference_row["temperature_f"],
                "humidity_pct": known_inference_row["humidity_pct"],
                "wind_mph": known_inference_row["wind_mph"],
                "precipitation_in": known_inference_row["precipitation_in"],
                "solar_radiation_mj_m2": known_inference_row["solar_radiation_mj_m2"],
                "rolling_temp_mean": known_inference_row["temperature_f"],
                "rolling_humidity_mean": known_inference_row["humidity_pct"],
                "rolling_precip_in": known_inference_row["precipitation_in"],
                "rolling_solar_mean": known_inference_row["solar_radiation_mj_m2"],
                "current_soil_moisture": current_vwc,
                "soil_moisture_lag_1": lag_1,
                "soil_moisture_lag_2": lag_2,
                "soil_moisture_delta_1": current_vwc - lag_1,
                "soil_moisture_delta_2": lag_1 - lag_2,
                "pump_capacity_in_per_hour": 0.236,
                "water_rights_schedule_count": 1,
                "energy_window_count": 1,
                "irrigation_type": known_inference_row["irrigation_type"],
                "soil_texture": known_inference_row["soil_texture"],
                "infiltration_rate_in_per_hour": 0.472,
                "slope_pct": 2.5,
                "drainage_class": "moderate",
                "crop_type": known_inference_row["crop_type"],
                "growth_stage": known_inference_row["growth_stage"],
                "max_irrigation_volume_in": 0.709,
                "field_area_acres": 59.3,
                "budget_dollars": 2800.0,
                "cumulative_irrigation_24h": 0.0,
                "cumulative_irrigation_72h": 0.0,
                "sensor_count": 1,
                "season_month": 7,
                "openet_monthly_et_in": 0.108,
            }
        ]
    )


def test_prediction_in_agronomic_range(known_inference_row):
    """Model output must fall within physically plausible VWC range."""
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.model_path.exists() or not settings.metadata_path.exists():
        pytest.skip("Model artifact not found — run train_model.py first")

    service = RecommendationService.from_artifacts(
        model_path=Path(settings.model_path),
        metadata_path=Path(settings.metadata_path),
    )
    features = build_inference_features(_build_known_feature_frame(known_inference_row))
    prediction = service.model.predict(features)

    assert 0.05 <= prediction["moisture_24h"] <= 0.55
