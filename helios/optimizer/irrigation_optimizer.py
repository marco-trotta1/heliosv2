"""
Rule-constrained irrigation optimizer.

Applies water-rights windows, pump capacity limits, infiltration rate constraints,
and soil saturation ceilings to generate a conservative horizon-aware irrigation recommendation.
Designed to support — not replace — operator judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helios.agronomy import SOIL_THRESHOLDS, gross_application_in, target_moisture


DEFAULT_COST_PER_IN_ACRE = 82.25  # $/in/acre (converted from $8/mm/ha)
HIGH_STRESS_THRESHOLD = 0.80
MIN_ACTIONABLE_AMOUNT_IN = 0.01


@dataclass
class OptimizationInputs:
    predicted_moisture: dict[str, float]
    stress_probability: float
    soil_texture: str
    infiltration_rate_in_per_hour: float
    pump_capacity_in_per_hour: float
    water_rights_schedule: list[str]
    energy_price_window: list[str]
    max_irrigation_volume_in: float
    field_area_acres: float
    budget_dollars: float
    estimated_et_in: float
    recent_precipitation_in: float
    model_rmse: float
    sensor_count: int
    physical_sensor_count: int
    irrigation_type: str = "pivot"
    growth_stage: str = "vegetative"
    drainage_class: str = "moderate"
    et_is_fallback: bool = False


def _allowed_hours(water_rights_schedule: list[str]) -> float:
    return max(1.0, min(12.0, float(len(water_rights_schedule) * 3)))


def _select_timing_window(water_rights_schedule: list[str], energy_price_window: list[str], needs_water: bool) -> str:
    if not needs_water:
        return "monitor next forecast cycle"
    overlap = [window for window in water_rights_schedule if window in energy_price_window]
    if overlap:
        return overlap[0]
    if water_rights_schedule:
        return water_rights_schedule[0]
    return "next available permitted window"


def _compute_budget_cap(field_area_acres: float, budget_dollars: float) -> float:
    if field_area_acres <= 0:
        return 0.0
    return budget_dollars / (DEFAULT_COST_PER_IN_ACRE * field_area_acres)


def _confidence_score(inputs: OptimizationInputs, dry_threshold: float, timing_window: str) -> float:
    base = max(0.2, 1.0 - min(inputs.model_rmse, 0.35) / 0.35)
    threshold_margin = abs(inputs.predicted_moisture["moisture_48h"] - dry_threshold)
    margin_bonus = min(0.2, threshold_margin / 0.15)
    if inputs.physical_sensor_count >= 3:
        sensor_penalty = 0.0
    elif inputs.physical_sensor_count == 2:
        sensor_penalty = 0.04
    else:
        sensor_penalty = 0.10
    timing_penalty = 0.05 if timing_window == "next available permitted window" else 0.0
    # Climatology-fallback ET is a regional average, not a field-specific reading;
    # surface that added uncertainty by trimming confidence.
    et_fallback_penalty = 0.05 if inputs.et_is_fallback else 0.0
    confidence = base + margin_bonus - sensor_penalty - timing_penalty - et_fallback_penalty
    return round(min(0.99, max(0.05, confidence)), 3)


def generate_irrigation_plan(inputs: OptimizationInputs) -> dict[str, Any]:
    thresholds = SOIL_THRESHOLDS.get(inputs.soil_texture, SOIL_THRESHOLDS["loam"])
    dry_threshold = thresholds["dry"]
    wet_threshold = thresholds["wet"]
    predicted_48h = inputs.predicted_moisture["moisture_48h"]
    predicted_72h = inputs.predicted_moisture["moisture_72h"]
    needs_water_48h = predicted_48h < dry_threshold
    needs_water_72h = predicted_72h < dry_threshold and inputs.stress_probability >= HIGH_STRESS_THRESHOLD
    needs_water = needs_water_48h or needs_water_72h
    decision_moisture = predicted_48h if needs_water_48h else predicted_72h

    timing_window = _select_timing_window(
        water_rights_schedule=inputs.water_rights_schedule,
        energy_price_window=inputs.energy_price_window,
        needs_water=needs_water,
    )

    # Crop water demand scales the ET buffer by growth-stage Kc (flowering pulls more
    # than emergence), matching the FAO-56 water balance used to build the training set.
    target = target_moisture(
        dry_threshold=dry_threshold,
        wet_threshold=wet_threshold,
        estimated_et_in=inputs.estimated_et_in,
        growth_stage=inputs.growth_stage,
    )
    deficit = max(0.0, target - decision_moisture)
    # Inverse application sizing uses the conservative REFILL_DEPTH (not the full root-zone
    # depletion depth) — see helios/agronomy and CONTEXT.md for why the two differ ~3.3x.
    raw_amount_in = gross_application_in(
        deficit=deficit,
        soil_texture=inputs.soil_texture,
        drainage_class=inputs.drainage_class,
        irrigation_type=inputs.irrigation_type,
    )

    pump_cap = inputs.pump_capacity_in_per_hour * _allowed_hours(inputs.water_rights_schedule)
    budget_cap = _compute_budget_cap(inputs.field_area_acres, inputs.budget_dollars)
    infiltration_soft_cap = inputs.infiltration_rate_in_per_hour * 2.5

    recommended_amount = min(
        raw_amount_in,
        inputs.max_irrigation_volume_in,
        pump_cap,
        budget_cap,
        infiltration_soft_cap,
    )
    if not needs_water:
        recommended_amount = 0.0

    rounded_amount = round(max(0.0, recommended_amount), 2)
    decision = "water" if needs_water and rounded_amount >= MIN_ACTIONABLE_AMOUNT_IN else "wait"
    if decision == "wait":
        rounded_amount = 0.0
        timing_window = _select_timing_window(
            water_rights_schedule=inputs.water_rights_schedule,
            energy_price_window=inputs.energy_price_window,
            needs_water=False,
        )

    confidence = _confidence_score(inputs, dry_threshold=dry_threshold, timing_window=timing_window)
    return {
        "decision": decision,
        "recommended_amount_in": rounded_amount,
        "timing_window": timing_window,
        "confidence_score": confidence,
        "soil_dry_threshold": dry_threshold,
        "soil_wet_threshold": wet_threshold,
    }
