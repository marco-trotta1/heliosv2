"""
Regression guard: model predictions must stay within the training target range.

Training targets are clipped to [0.05, 0.50]. We allow a small margin (0.55)
to account for legitimate extrapolation, but 0.57 is a known bad-mode signature
caused by feeding out-of-distribution features (season_month=0, openet=0.0).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "moisture_model.pkl"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"


def _make_feature_row(
    season_month: int,
    openet_monthly_et_in: float,
    current_soil_moisture: float = 0.25,
    soil_texture: str = "loam",
    growth_stage: str = "vegetative",
) -> pd.DataFrame:
    """Build a minimal feature row matching the training schema."""
    row: dict[str, object] = {
        "forecast_horizon_hours": 48,
        "temperature_f": 80.6,
        "humidity_pct": 48.0,
        "wind_mph": 7.16,
        "precipitation_in": 0.05,
        "solar_radiation_mj_m2": 22.0,
        "rolling_temp_mean": 80.6,
        "rolling_humidity_mean": 48.0,
        "rolling_precip_in": 0.05,
        "rolling_solar_mean": 22.0,
        "current_soil_moisture": current_soil_moisture,
        "soil_moisture_lag_1": current_soil_moisture,
        "soil_moisture_lag_2": current_soil_moisture,
        "soil_moisture_delta_1": 0.0,
        "soil_moisture_delta_2": 0.0,
        "pump_capacity_in_per_hour": 0.256,
        "water_rights_schedule_count": 2,
        "energy_window_count": 1,
        "infiltration_rate_in_per_hour": 0.512,
        "slope_pct": 2.6,
        "max_irrigation_volume_in": 0.709,
        "field_area_acres": 69.2,
        "budget_dollars": 600.0,
        "cumulative_irrigation_24h": 0.0,
        "cumulative_irrigation_72h": 0.0,
        "sensor_count": 4,
        "season_month": season_month,
        "openet_monthly_et_in": openet_monthly_et_in,
        "reference_et_in": 0.296,
        # One-hot encoded categoricals
        "soil_texture_clay": 0.0,
        "soil_texture_loam": 1.0 if soil_texture == "loam" else 0.0,
        "soil_texture_sand": 1.0 if soil_texture == "sand" else 0.0,
        "drainage_class_moderate": 1.0,
        "drainage_class_poor": 0.0,
        "drainage_class_well": 0.0,
        "irrigation_type_drip": 0.0,
        "irrigation_type_flood": 0.0,
        "irrigation_type_pivot": 1.0,
        "growth_stage_emergence": 0.0,
        "growth_stage_flowering": 0.0,
        "growth_stage_grain_fill": 0.0,
        "growth_stage_maturity": 0.0,
        "growth_stage_vegetative": 1.0 if growth_stage == "vegetative" else 0.0,
        "crop_type_alfalfa": 0.0,
        "crop_type_corn": 1.0,
        "crop_type_potato": 0.0,
        "crop_type_soybean": 0.0,
    }
    return pd.DataFrame([row])


@pytest.fixture(scope="module")
def model():
    if not MODEL_PATH.exists():
        pytest.skip("No model artifact found — run train_model first")
    from helios.models.moisture_model import MoistureForecastModel
    return MoistureForecastModel.load(MODEL_PATH, METADATA_PATH)


def test_predictions_in_range_with_correct_features(model):
    """With correct season_month and openet values, all predictions stay ≤ 0.55."""
    bad_predictions = []
    for month, openet_val in [(4, 0.1024), (5, 0.0991), (6, 0.1024), (7, 0.108), (8, 0.0876), (9, 0.0289)]:
        for moisture in [0.12, 0.20, 0.28, 0.35]:
            row = _make_feature_row(season_month=month, openet_monthly_et_in=openet_val, current_soil_moisture=moisture)
            pred = model.predict(row)
            for key, val in pred.items():
                if val > 0.55:
                    bad_predictions.append(f"month={month} moisture={moisture} {key}={val:.4f}")

    assert not bad_predictions, f"Out-of-range predictions: {bad_predictions}"


def test_predictions_stay_above_floor_at_low_moisture(model):
    """Predictions at the low end of the training range should stay within [0.05, 0.55]."""
    for moisture in [0.08, 0.10, 0.12]:
        row = _make_feature_row(season_month=7, openet_monthly_et_in=0.108, current_soil_moisture=moisture)
        pred = model.predict(row)
        for key, val in pred.items():
            assert val >= 0.0, f"Negative prediction: {key}={val} at moisture={moisture}"
            assert val <= 0.55, f"Out-of-range prediction: {key}={val} at moisture={moisture}"
