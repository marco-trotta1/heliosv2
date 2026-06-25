"""Demo/backend parity: the browser demo policy must match the Python backend policy.

Feeds a curated scenario grid (plus preset-derived cases) through both the Python optimizer
(+ agronomy stress/drivers) and the JS demo policy (run via Node), and asserts identical
decision, amount, timing, confidence, stress, and which drivers fired. This is what proves
the two hand-fixed formula gaps are actually closed and stay closed.

Requires `node` on PATH. CI (ubuntu-latest) has it; locally the test skips if absent. The
pure-Python constant guard (test_frontend_constants_generated.py) always runs regardless.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from helios import agronomy
from helios.optimizer.irrigation_optimizer import OptimizationInputs, generate_irrigation_plan

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_JS = REPO_ROOT / "tests" / "parity" / "run_js.mjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")

# Drivers are intentionally worded differently in JS (prose) vs Python (terse), so parity
# compares which rules fired, not the strings. Map both vocabularies to shared rule ids.
PY_DRIVER_RULE = {
    "high evapotranspiration": "high_et",
    "low soil moisture": "low_moisture",
    "limited forecast precipitation": "low_precip",
    "restrictive water rights window": "narrow_window",
    "sensitive crop growth stage": "sensitive_stage",
    "continued drying trend": "drying_trend",
    "stable near-threshold moisture": "stable",
}
JS_DRIVER_RULE = {
    "High evapotranspiration is pulling moisture down quickly.": "high_et",
    "Current soil moisture is already near the crop stress band.": "low_moisture",
    "Very little forecast rain is expected to refill the root zone.": "low_precip",
    "The field has a narrow irrigation availability window.": "narrow_window",
    "The crop is in a yield-sensitive growth stage.": "sensitive_stage",
    "The full 72-hour trend keeps moving drier.": "drying_trend",
    "Conditions are stable enough to keep watching instead of watering now.": "stable",
}


def _base():
    return {
        "soil_texture": "loam",
        "drainage_class": "moderate",
        "irrigation_type": "pivot",
        "growth_stage": "flowering",
        "predicted": {"moisture_24h": 0.19, "moisture_48h": 0.16, "moisture_72h": 0.14},
        "estimated_et_in": 0.22,
        "water_window": ["tonight", "tomorrow_morning"],
        "energy_window": ["tonight"],
        "max_irrigation_volume_in": 0.71,
        "pump_capacity_in_per_hour": 0.24,
        "field_area_acres": 59.3,
        "budget_dollars": 2800.0,
        "infiltration_rate_in_per_hour": 0.47,
        "model_rmse": 0.12,
        "sensor_count": 3,
        "current_moisture": 0.18,
        "precipitation_in": 0.0,
    }


def _scenarios():
    scenarios = []
    dry = {"moisture_24h": 0.19, "moisture_48h": 0.15, "moisture_72h": 0.13}
    wet = {"moisture_24h": 0.30, "moisture_48h": 0.33, "moisture_72h": 0.35}

    # texture x drainage x {dry->water, wet->wait}
    for texture in ("sand", "loam", "clay"):
        for drainage in ("poor", "moderate", "well"):
            for predicted in (dry, wet):
                s = _base()
                s.update(soil_texture=texture, drainage_class=drainage, predicted=dict(predicted))
                scenarios.append(s)

    # stage x irrigation type, drying
    for stage in ("emergence", "vegetative", "flowering", "grain_fill", "maturity"):
        for irr in ("pivot", "drip", "flood"):
            s = _base()
            s.update(growth_stage=stage, irrigation_type=irr, predicted=dict(dry))
            scenarios.append(s)

    # edge cases
    edge_no_windows = _base()
    edge_no_windows.update(water_window=[], energy_window=[], predicted=dict(dry))
    scenarios.append(edge_no_windows)

    edge_tiny_budget = _base()
    edge_tiny_budget.update(budget_dollars=40.0, predicted=dict(dry))
    scenarios.append(edge_tiny_budget)

    edge_one_window = _base()
    edge_one_window.update(water_window=["tonight"], predicted=dict(dry))
    scenarios.append(edge_one_window)

    # preset-derived cases (mirror src/constants.js PRESETS)
    heatwave = _base()
    heatwave.update(soil_texture="loam", growth_stage="flowering", irrigation_type="pivot",
                    estimated_et_in=0.30, budget_dollars=3000.0, predicted=dict(dry))
    scenarios.append(heatwave)

    balanced = _base()
    balanced.update(soil_texture="loam", growth_stage="vegetative", irrigation_type="drip",
                    current_moisture=0.27, precipitation_in=0.11, predicted=dict(wet))
    scenarios.append(balanced)

    kimberly = _base()
    kimberly.update(soil_texture="loam", growth_stage="flowering", irrigation_type="pivot",
                    max_irrigation_volume_in=2.0, predicted=dict(dry))
    scenarios.append(kimberly)

    rain = _base()
    rain.update(soil_texture="clay", drainage_class="poor", growth_stage="grain_fill",
                infiltration_rate_in_per_hour=0.28, precipitation_in=0.43,
                current_moisture=0.31, predicted=dict(wet))
    scenarios.append(rain)

    return scenarios


def _python_outputs(s):
    dry_threshold = agronomy.SOIL_THRESHOLDS[s["soil_texture"]]["dry"]
    predicted = {
        "moisture_24h": s["predicted"]["moisture_24h"],
        "moisture_48h": s["predicted"]["moisture_48h"],
        "moisture_72h": s["predicted"]["moisture_72h"],
    }
    stress = agronomy.stress_probability(
        predicted_moisture_48h=predicted["moisture_48h"],
        dry_threshold=dry_threshold,
        estimated_et_in=s["estimated_et_in"],
        growth_stage=s["growth_stage"],
    )
    plan = generate_irrigation_plan(
        OptimizationInputs(
            predicted_moisture=predicted,
            stress_probability=stress,
            soil_texture=s["soil_texture"],
            infiltration_rate_in_per_hour=s["infiltration_rate_in_per_hour"],
            pump_capacity_in_per_hour=s["pump_capacity_in_per_hour"],
            water_rights_schedule=s["water_window"],
            energy_price_window=s["energy_window"],
            max_irrigation_volume_in=s["max_irrigation_volume_in"],
            field_area_acres=s["field_area_acres"],
            budget_dollars=s["budget_dollars"],
            estimated_et_in=s["estimated_et_in"],
            recent_precipitation_in=s["precipitation_in"],
            model_rmse=s["model_rmse"],
            sensor_count=s["sensor_count"],
            physical_sensor_count=s["sensor_count"],
            irrigation_type=s["irrigation_type"],
            growth_stage=s["growth_stage"],
            drainage_class=s["drainage_class"],
            et_is_fallback=False,
        )
    )
    drivers = agronomy.drivers(
        estimated_et_in=s["estimated_et_in"],
        current_moisture=s["current_moisture"],
        soil_texture=s["soil_texture"],
        precipitation_in=s["precipitation_in"],
        water_rights_window_count=len(s["water_window"]),
        growth_stage=s["growth_stage"],
        stress_probability=stress,
        predicted_moisture_24h=predicted["moisture_24h"],
        predicted_moisture_72h=predicted["moisture_72h"],
    )
    return {
        "stress": stress,
        "decision": plan["decision"],
        "recommended_amount_in": plan["recommended_amount_in"],
        "timing_window": plan["timing_window"],
        "confidence_score": plan["confidence_score"],
        "drivers": [PY_DRIVER_RULE[d] for d in drivers],
    }


def test_demo_matches_backend_policy():
    scenarios = _scenarios()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(scenarios, fh)
        scenarios_path = fh.name

    proc = subprocess.run(
        ["node", str(RUN_JS), scenarios_path],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, f"node harness failed:\n{proc.stderr}"
    js_results = json.loads(proc.stdout)

    assert len(js_results) == len(scenarios)
    mismatches = []
    for s, js in zip(scenarios, js_results):
        py = _python_outputs(s)
        js_drivers = [JS_DRIVER_RULE[d] for d in js["drivers"]]
        label = f"{s['soil_texture']}/{s['drainage_class']}/{s['growth_stage']}/{s['irrigation_type']} pred={s['predicted']['moisture_48h']}"
        if py["decision"] != js["decision"]:
            mismatches.append(f"{label}: decision {py['decision']} != {js['decision']}")
        if abs(py["recommended_amount_in"] - js["recommended_amount_in"]) > 1e-9:
            mismatches.append(f"{label}: amount {py['recommended_amount_in']} != {js['recommended_amount_in']}")
        if py["timing_window"] != js["timing_window"]:
            mismatches.append(f"{label}: timing {py['timing_window']!r} != {js['timing_window']!r}")
        if abs(py["confidence_score"] - js["confidence_score"]) > 1e-9:
            mismatches.append(f"{label}: confidence {py['confidence_score']} != {js['confidence_score']}")
        if abs(py["stress"] - js["stress"]) > 1e-9:
            mismatches.append(f"{label}: stress {py['stress']} != {js['stress']}")
        if py["drivers"] != js_drivers:
            mismatches.append(f"{label}: drivers {py['drivers']} != {js_drivers}")

    assert not mismatches, "demo/backend parity broken:\n" + "\n".join(mismatches)
