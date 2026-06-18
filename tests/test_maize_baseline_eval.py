from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from helios.scripts.evaluate_maize_baseline import evaluate_maize_baseline, resolve_verdict


def _build_row(
    *,
    field_id: str,
    source_id: str,
    prediction_time: str,
    current_soil_moisture: float,
    target_moisture_24h: float,
    target_moisture_48h: float,
    target_moisture_72h: float,
    target_source_24h: str,
    target_source_48h: str,
    target_source_72h: str,
    season_month: int,
    crop_type: str,
    growth_stage: str,
    soil_texture: str,
    irrigation_type: str,
    drainage_class: str,
    temperature_f: float,
    humidity_pct: float,
    wind_mph: float,
    solar_radiation_mj_m2: float,
    openet_monthly_et_in: float,
) -> dict[str, object]:
    return {
        "field_id": field_id,
        "source_id": source_id,
        "prediction_time": prediction_time,
        "forecast_horizon_hours": 72,
        "temperature_f": temperature_f,
        "humidity_pct": humidity_pct,
        "wind_mph": wind_mph,
        "precipitation_in": 0.02,
        "solar_radiation_mj_m2": solar_radiation_mj_m2,
        "rolling_temp_mean": temperature_f - 1.0,
        "rolling_humidity_mean": humidity_pct + 2.0,
        "rolling_precip_in": 0.03,
        "rolling_solar_mean": solar_radiation_mj_m2 - 1.0,
        "current_soil_moisture": current_soil_moisture,
        "soil_moisture_lag_1": current_soil_moisture + 0.01,
        "soil_moisture_lag_2": current_soil_moisture + 0.02,
        "soil_moisture_delta_1": -0.01,
        "soil_moisture_delta_2": -0.01,
        "moisture_min": current_soil_moisture - 0.01,
        "moisture_max": current_soil_moisture + 0.02,
        "moisture_mean": current_soil_moisture + 0.005,
        "moisture_spread": 0.03,
        "physical_sensor_count": 2,
        "pump_capacity_in_per_hour": 0.25,
        "water_rights_schedule_count": 1,
        "energy_window_count": 1,
        "irrigation_type": irrigation_type,
        "soil_texture": soil_texture,
        "infiltration_rate_in_per_hour": 0.5,
        "slope_pct": 2.0,
        "drainage_class": drainage_class,
        "crop_type": crop_type,
        "growth_stage": growth_stage,
        "max_irrigation_volume_in": 1.0,
        "field_area_acres": 120.0,
        "budget_dollars": 800.0,
        "cumulative_irrigation_24h": 0.08,
        "cumulative_irrigation_72h": 0.20,
        "sensor_count": 2,
        "season_month": season_month,
        "openet_monthly_et_in": openet_monthly_et_in,
        "reference_et_in": max(openet_monthly_et_in - 0.01, 0.01),
        "target_source_24h": target_source_24h,
        "target_source_48h": target_source_48h,
        "target_source_72h": target_source_72h,
        "target_moisture_24h": target_moisture_24h,
        "target_moisture_48h": target_moisture_48h,
        "target_moisture_72h": target_moisture_72h,
    }


def _write_base_fixture(path: Path) -> None:
    rows: list[dict[str, object]] = []
    for group_index, field_id in enumerate(["synthetic-a", "synthetic-b", "mickelson-a", "mickelson-b"]):
        source_id = "synthetic" if field_id.startswith("synthetic") else "mickelson"
        for day_index in range(3):
            current = 0.23 + (group_index * 0.01) + (day_index * 0.004)
            rows.append(
                _build_row(
                    field_id=field_id,
                    source_id=source_id,
                    prediction_time=f"2024-07-{day_index + 1:02d}T12:00:00Z",
                    current_soil_moisture=current,
                    target_moisture_24h=current - 0.006,
                    target_moisture_48h=current - 0.012,
                    target_moisture_72h=current - 0.018,
                    target_source_24h="synthetic_generated",
                    target_source_48h="synthetic_generated",
                    target_source_72h="synthetic_generated",
                    season_month=7,
                    crop_type="potato" if source_id == "synthetic" else "spring_grain",
                    growth_stage="flowering",
                    soil_texture="loam",
                    irrigation_type="pivot",
                    drainage_class="moderate",
                    temperature_f=78.0 + group_index,
                    humidity_pct=42.0 + day_index,
                    wind_mph=6.0 + group_index,
                    solar_radiation_mj_m2=21.0 + day_index,
                    openet_monthly_et_in=0.13 + (group_index * 0.01),
                )
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_maize_fixture(path: Path) -> None:
    rows: list[dict[str, object]] = []
    maize_groups = [
        ("usda_lirf_2012_trt_1", 2012, 6, 0.19),
        ("usda_lirf_2012_trt_2", 2012, 7, 0.21),
        ("usda_lirf_2013_trt_1", 2013, 6, 0.20),
        ("usda_lirf_2013_trt_2", 2013, 7, 0.22),
    ]
    for group_index, (field_id, year, season_month, base_current) in enumerate(maize_groups):
        for day_index in range(3):
            current = base_current + (day_index * 0.004)
            rows.append(
                _build_row(
                    field_id=field_id,
                    source_id="usda_lirf_2012_2013",
                    prediction_time=f"{year}-06-{day_index + 10:02d}T12:00:00Z",
                    current_soil_moisture=current,
                    target_moisture_24h=current - 0.004,
                    target_moisture_48h=current - 0.009,
                    target_moisture_72h=current - 0.013,
                    target_source_24h="root_zone_weighted_swc" if day_index != 1 else "root_zone_weighted_swc_daily_interpolated",
                    target_source_48h="root_zone_weighted_swc",
                    target_source_72h="root_zone_weighted_swc",
                    season_month=season_month,
                    crop_type="corn",
                    growth_stage="vegetative" if day_index == 0 else "flowering",
                    soil_texture="loam",
                    irrigation_type="pivot",
                    drainage_class="moderate",
                    temperature_f=79.0 + group_index,
                    humidity_pct=38.0 + day_index,
                    wind_mph=5.5 + group_index,
                    solar_radiation_mj_m2=22.0 + day_index,
                    openet_monthly_et_in=0.16 + (group_index * 0.01),
                )
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_evaluate_maize_baseline_smoke_emits_reports_and_metrics(tmp_path: Path) -> None:
    base_csv = tmp_path / "base.csv"
    maize_csv = tmp_path / "maize.csv"
    out_json = tmp_path / "maize_eval.json"
    out_md = tmp_path / "maize_eval.md"

    _write_base_fixture(base_csv)
    _write_maize_fixture(maize_csv)

    result = evaluate_maize_baseline(
        base_csv=str(base_csv),
        maize_csv=str(maize_csv),
        out_json=str(out_json),
        out_md=str(out_md),
        n_estimators=5,
        learning_rate=0.1,
    )

    assert out_json.exists()
    assert out_md.exists()
    assert json.loads(out_json.read_text()) == result
    assert result["verdict"] in {"CANDIDATE_PASS", "CANDIDATE_FAIL"}

    group_kfold = result["protocols"]["group_kfold"]
    measured_48h = group_kfold["summary"]["measured_only"]["48h"]
    assert measured_48h["count"] > 0

    for protocol_name in ("group_kfold", "loyo"):
        protocol = result["protocols"][protocol_name]
        for subset_name in ("measured_only", "interpolated_included"):
            for horizon in ("24h", "48h", "72h"):
                metrics = protocol["summary"][subset_name][horizon]
                assert math.isfinite(metrics["baseline_mae"])
                assert math.isfinite(metrics["candidate_mae"])
                assert math.isfinite(metrics["baseline_bias"])
                assert math.isfinite(metrics["candidate_bias"])
                assert math.isfinite(metrics["baseline_rmse"])
                assert math.isfinite(metrics["candidate_rmse"])
                assert math.isfinite(metrics["delta_mae"])
                assert metrics["delta_mae"] == round(metrics["baseline_mae"] - metrics["candidate_mae"], 6)

    for fold in group_kfold["folds"]:
        assert set(fold["holdout_groups"]).isdisjoint(set(fold["train_groups"]))


def test_resolve_verdict_fails_when_candidate_does_not_beat_persistence() -> None:
    verdict, reasons = resolve_verdict(
        protocols={
            "group_kfold": {"gates": {"measured_48h_count_nonzero": True, "measured_72h_count_nonzero": True, "measured_threshold_pass": True, "persistence_pass": False}},
            "loyo": {"gates": {"measured_48h_count_nonzero": True, "measured_72h_count_nonzero": True, "measured_threshold_pass": True, "persistence_pass": True}},
        },
        base_no_regression={"pass": True},
        transfer_proxy={"candidate_better": False},
    )

    assert verdict == "CANDIDATE_FAIL"
    assert any("persistence" in reason for reason in reasons)


def test_resolve_verdict_fails_when_base_no_regression_gate_misses_threshold() -> None:
    verdict, reasons = resolve_verdict(
        protocols={
            "group_kfold": {"gates": {"measured_48h_count_nonzero": True, "measured_72h_count_nonzero": True, "measured_threshold_pass": True, "persistence_pass": True}},
            "loyo": {"gates": {"measured_48h_count_nonzero": True, "measured_72h_count_nonzero": True, "measured_threshold_pass": True, "persistence_pass": True}},
        },
        base_no_regression={"pass": False, "candidate_rmse_mean": 0.091, "baseline_rmse_mean": 0.088},
        transfer_proxy={"candidate_better": True},
    )

    assert verdict == "CANDIDATE_FAIL"
    assert any("no-regression" in reason for reason in reasons)
