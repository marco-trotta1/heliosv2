from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from helios.data.feature_engineering import TARGET_COLUMNS, build_inference_features
from helios.models.moisture_model import MoistureForecastModel
from helios.models.train_model import _build_targets_for_mode
from helios.scripts.run_pre_pilot_baseline_experiment import run_pre_pilot_baseline_experiment
from helios.simulation.season import generate_simulated_seasons, seasons_to_training_rows


class ConstantDeltaModel:
    def predict(self, matrix: pd.DataFrame) -> np.ndarray:
        return np.array([[0.03, -0.02, 0.40] for _ in range(len(matrix))])


def test_simulated_seasons_are_deterministic_for_seed_42() -> None:
    first = generate_simulated_seasons(seasons=3, seed=42, engine="internal_fao56")
    second = generate_simulated_seasons(seasons=3, seed=42, engine="internal_fao56")

    pd.testing.assert_frame_equal(first, second)
    assert set(first["engine_used"]) == {"internal_fao56"}
    assert first["field_id"].nunique() == 3


def test_simulated_training_rows_use_origin_features_and_future_labels() -> None:
    seasons = generate_simulated_seasons(seasons=1, seed=42, engine="internal_fao56")

    rows = seasons_to_training_rows(seasons, source_id="synthetic_fao56_season")

    first_row = rows.iloc[0]
    origin_time = pd.Timestamp(first_row["prediction_time"])
    origin = seasons[seasons["date"].eq(origin_time)].iloc[0]
    plus_1 = seasons[seasons["date"].eq(origin_time + pd.Timedelta(days=1))].iloc[0]
    plus_2 = seasons[seasons["date"].eq(origin_time + pd.Timedelta(days=2))].iloc[0]
    plus_3 = seasons[seasons["date"].eq(origin_time + pd.Timedelta(days=3))].iloc[0]

    assert first_row["source_id"] == "synthetic_fao56_season"
    assert first_row["current_soil_moisture"] == origin["soil_moisture"]
    assert first_row["target_moisture_24h"] == plus_1["soil_moisture"]
    assert first_row["target_moisture_48h"] == plus_2["soil_moisture"]
    assert first_row["target_moisture_72h"] == plus_3["soil_moisture"]
    assert set(rows[["target_source_24h", "target_source_48h", "target_source_72h"]].stack()) == {
        "fao56_season_simulated"
    }
    assert rows[["source_id", "field_id", "prediction_time"]].notna().all().all()
    assert rows[TARGET_COLUMNS].min().min() >= 0.05
    assert rows[TARGET_COLUMNS].max().max() <= 0.50


def test_target_mode_raw_preserves_targets_and_residual_mode_trains_deltas() -> None:
    frame = pd.DataFrame(
        {
            "current_soil_moisture": [0.21, 0.33],
            "target_moisture_24h": [0.23, 0.30],
            "target_moisture_48h": [0.24, 0.29],
            "target_moisture_72h": [0.25, 0.28],
        }
    )
    raw_targets = frame[TARGET_COLUMNS]

    raw = _build_targets_for_mode(frame, raw_targets, target_mode="raw")
    residual = _build_targets_for_mode(frame, raw_targets, target_mode="residual_from_current")

    pd.testing.assert_frame_equal(raw, raw_targets)
    expected = pd.DataFrame(
        {
            "target_moisture_24h": [0.02, -0.03],
            "target_moisture_48h": [0.03, -0.04],
            "target_moisture_72h": [0.04, -0.05],
        }
    )
    pd.testing.assert_frame_equal(residual.round(4), expected)


def test_residual_prediction_adds_current_moisture_and_clips_to_texture_bounds() -> None:
    raw = pd.DataFrame(
        [
            {
                "field_id": "field-001",
                "current_soil_moisture": 0.20,
                "soil_moisture_lag_1": 0.19,
                "soil_moisture_lag_2": 0.18,
                "soil_moisture_delta_1": 0.01,
                "soil_moisture_delta_2": 0.01,
                "moisture_min": 0.18,
                "moisture_max": 0.21,
                "moisture_mean": 0.195,
                "moisture_spread": 0.03,
                "physical_sensor_count": 2,
                "forecast_horizon_hours": 72,
                "temperature_f": 82.0,
                "humidity_pct": 40.0,
                "wind_mph": 7.0,
                "precipitation_in": 0.0,
                "solar_radiation_mj_m2": 24.0,
                "rolling_temp_mean": 82.0,
                "rolling_humidity_mean": 40.0,
                "rolling_precip_in": 0.0,
                "rolling_solar_mean": 24.0,
                "pump_capacity_in_per_hour": 0.25,
                "water_rights_schedule_count": 1,
                "energy_window_count": 1,
                "irrigation_type": "pivot",
                "soil_texture": "loam",
                "infiltration_rate_in_per_hour": 0.5,
                "slope_pct": 2.0,
                "drainage_class": "moderate",
                "crop_type": "corn",
                "growth_stage": "flowering",
                "max_irrigation_volume_in": 0.7,
                "field_area_acres": 80.0,
                "budget_dollars": 600.0,
                "cumulative_irrigation_24h": 0.0,
                "cumulative_irrigation_72h": 0.0,
                "sensor_count": 2,
                "season_month": 7,
                "openet_monthly_et_in": 0.1,
                "reference_et_in": 0.2,
            }
        ]
    )
    features = build_inference_features(raw)
    wrapper = MoistureForecastModel(
        model=ConstantDeltaModel(),
        feature_columns=list(features.columns),
        metadata={"target_mode": "residual_from_current"},
    )

    prediction = wrapper.predict(features)

    assert prediction == pytest.approx({
        "moisture_24h": 0.23,
        "moisture_48h": 0.18,
        "moisture_72h": 0.42,
    })


def test_pre_pilot_experiment_writes_candidate_outputs_without_touching_shipped_artifacts(tmp_path: Path) -> None:
    shipped_model = tmp_path / "shipped" / "moisture_model.pkl"
    shipped_metadata = tmp_path / "shipped" / "model_metadata.json"
    shipped_model.parent.mkdir(parents=True)
    shipped_model.write_bytes(b"do-not-touch-model")
    shipped_metadata.write_text('{"status": "do-not-touch"}')

    result = run_pre_pilot_baseline_experiment(
        output_root=tmp_path / "data" / "candidates" / "pre_pilot",
        artifact_root=tmp_path / "artifacts" / "candidates" / "pre_pilot",
        seasons=8,
        seed=42,
        engine="auto",
        target_mode="residual_from_current",
        n_estimators=5,
        learning_rate=0.1,
        shipped_model_path=shipped_model,
        shipped_metadata_path=shipped_metadata,
    )

    expected_data = [
        "simulated_seasons.csv",
        "simulated_training.csv",
        "combined_training.csv",
    ]
    expected_artifacts = [
        "moisture_model.pkl",
        "model_metadata.json",
        "pre_pilot_baseline_report.json",
        "pre_pilot_baseline_report.md",
    ]
    for name in expected_data:
        assert (tmp_path / "data" / "candidates" / "pre_pilot" / name).exists()
    for name in expected_artifacts:
        assert (tmp_path / "artifacts" / "candidates" / "pre_pilot" / name).exists()

    metadata = json.loads((tmp_path / "artifacts" / "candidates" / "pre_pilot" / "model_metadata.json").read_text())
    report = json.loads(
        (tmp_path / "artifacts" / "candidates" / "pre_pilot" / "pre_pilot_baseline_report.json").read_text()
    )

    assert metadata["target_mode"] == "residual_from_current"
    assert report["shipping_rule"] == "candidate_only_no_shipped_artifact_replacement"
    assert report["leaderboard"]
    assert {"persistence", "physics_only", "current_shipped_model", "residual_candidate", "report_only_ensemble"}.issubset(
        {entry["model"] for entry in report["leaderboard"]}
    )
    assert result["combined_rows"] == len(pd.read_csv(tmp_path / "data" / "candidates" / "pre_pilot" / "combined_training.csv"))
    assert shipped_model.read_bytes() == b"do-not-touch-model"
    assert shipped_metadata.read_text() == '{"status": "do-not-touch"}'
    assert joblib.load(tmp_path / "artifacts" / "candidates" / "pre_pilot" / "moisture_model.pkl")
