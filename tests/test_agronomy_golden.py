"""Golden-master guard for the agronomy consolidation.

The fixture in tests/fixtures/agronomy_golden.json was captured from the pre-refactor
implementations (the four scattered copies of the water balance). These tests assert the
consolidated helios/agronomy module — and the callers rewired onto it — reproduce those
outputs byte-for-byte. That is the proof that the refactor required no model retrain and no
field re-validation. If a value here changes, behavior changed: stop and re-validate.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from helios import agronomy
from helios.optimizer.irrigation_optimizer import OptimizationInputs, generate_irrigation_plan
from helios.scripts.generate_sample_data import generate_sample_data
from helios.scripts.mickelson_support import (
    DEFAULT_DRAINAGE_CLASS,
    DEFAULT_IRRIGATION_TYPE,
    DEFAULT_SOIL_TEXTURE,
    daily_moisture_step,
)

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "agronomy_golden.json").read_text())


def test_daily_moisture_step_unchanged():
    for m, et, precip, irr, stage, expected in GOLDEN["daily_moisture_step"]:
        got = daily_moisture_step(
            m, daily_precip_in=precip, daily_irrigation_in=irr,
            daily_reference_et_in=et, growth_stage=stage,
        )
        assert got == expected, (m, et, precip, irr, stage)


def test_generate_irrigation_plan_unchanged():
    base = dict(
        predicted_moisture={"moisture_24h": 0.19, "moisture_48h": 0.16, "moisture_72h": 0.14},
        stress_probability=0.85, soil_texture="loam", infiltration_rate_in_per_hour=0.5,
        pump_capacity_in_per_hour=0.25, water_rights_schedule=["tonight", "tomorrow_morning"],
        energy_price_window=["tonight"], max_irrigation_volume_in=0.7, field_area_acres=60.0,
        budget_dollars=2800.0, estimated_et_in=0.22, recent_precipitation_in=0.0,
        model_rmse=0.12, sensor_count=3, physical_sensor_count=3,
        irrigation_type="pivot", growth_stage="flowering", drainage_class="moderate", et_is_fallback=False,
    )
    for variant, expected in GOLDEN["generate_irrigation_plan"]:
        plan = generate_irrigation_plan(OptimizationInputs(**{**base, **variant}))
        assert plan == expected, variant


def test_stress_probability_unchanged():
    for p48, dry, et, stage, expected in GOLDEN["stress_probability"]:
        got = agronomy.stress_probability(
            predicted_moisture_48h=p48, dry_threshold=dry,
            estimated_et_in=et, growth_stage=stage,
        )
        assert got == expected, (p48, dry, et, stage)


def test_drivers_unchanged():
    for soil, precip, window_count, stage, predicted, stress, et, cur, expected in GOLDEN["drivers"]:
        got = agronomy.drivers(
            estimated_et_in=et, current_moisture=cur, soil_texture=soil,
            precipitation_in=precip, water_rights_window_count=window_count,
            growth_stage=stage, stress_probability=stress,
            predicted_moisture_24h=predicted["moisture_24h"],
            predicted_moisture_72h=predicted["moisture_72h"],
        )
        assert got == expected, (soil, stage)


def test_step_forward_matches_baked_mickelson_defaults():
    # daily_moisture_step is now a thin clamp over step_forward with loam/moderate/pivot.
    raw = agronomy.step_forward(
        0.30, reference_et_in=0.25, precip_in=0.1, irrigation_in=0.2,
        growth_stage="flowering", soil_texture=DEFAULT_SOIL_TEXTURE,
        drainage_class=DEFAULT_DRAINAGE_CLASS, irrigation_type=DEFAULT_IRRIGATION_TYPE,
    )
    clamped = daily_moisture_step(
        0.30, daily_precip_in=0.1, daily_irrigation_in=0.2,
        daily_reference_et_in=0.25, growth_stage="flowering",
    )
    assert clamped == pytest.approx(max(0.10, min(0.45, raw)))


def test_generate_sample_data_targets_unchanged():
    tmp = os.path.join(tempfile.gettempdir(), "golden_sample_check.csv")
    frame = generate_sample_data(rows=6, output_path=tmp, seed=42)
    got = frame[["target_moisture_24h", "target_moisture_48h", "target_moisture_72h"]].values.tolist()
    assert got == GOLDEN["generate_sample_data_targets"]
