from __future__ import annotations

from pathlib import Path

import pandas as pd

from helios.scripts.score_validation_results import score_validation_data


def test_score_validation_reports_missing_field_data(tmp_path: Path) -> None:
    result = score_validation_data(str(tmp_path / "missing.csv"))

    assert result["status"] == "CANNOT SCORE: missing field validation data"
    assert result["metrics"] == {}


def test_score_validation_uses_reference_probe_rule(tmp_path: Path) -> None:
    input_path = tmp_path / "validation.csv"
    pd.DataFrame(
        [
            {
                "run_id": "run-1",
                "horizon_hours": 24,
                "predicted_vwc": 0.24,
                "observed_vwc": 0.23,
                "sensor_id": "sensor-a",
                "reference_probe": True,
                "helios_decision": "water",
                "researcher_judgment": "water",
            },
            {
                "run_id": "run-1",
                "horizon_hours": 24,
                "predicted_vwc": 0.24,
                "observed_vwc": 0.28,
                "sensor_id": "sensor-b",
                "reference_probe": False,
                "helios_decision": "water",
                "researcher_judgment": "water",
            },
        ]
    ).to_csv(input_path, index=False)

    result = score_validation_data(str(input_path))

    assert result["status"] == "VALIDATED"
    assert result["reference_rule"] == "reference_probe"
    assert result["metrics"]["mae_by_horizon"]["24"] == 0.01
    assert result["metrics"]["bias_by_horizon"]["24"] == 0.01
    assert result["metrics"]["out_of_range_predictions"] == 0
    assert result["metrics"]["water_wait_agreement"] == 1.0


def test_score_validation_auto_falls_back_to_driest_sensor(tmp_path: Path) -> None:
    input_path = tmp_path / "validation.csv"
    pd.DataFrame(
        [
            {"run_id": "run-1", "horizon_hours": 48, "predicted_vwc": 0.20, "observed_vwc": 0.22, "sensor_id": "a"},
            {"run_id": "run-1", "horizon_hours": 48, "predicted_vwc": 0.20, "observed_vwc": 0.18, "sensor_id": "b"},
        ]
    ).to_csv(input_path, index=False)

    result = score_validation_data(str(input_path))

    assert result["status"] == "PROMISING BUT NOT VALIDATED"
    assert result["reference_rule"] == "driest"
    assert result["metrics"]["mae_by_horizon"]["48"] == 0.02
