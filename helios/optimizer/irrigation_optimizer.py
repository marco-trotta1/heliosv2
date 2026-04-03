"""
Rule-constrained irrigation optimizer.

Applies water-rights windows, pump capacity limits, infiltration rate constraints,
and soil saturation ceilings to generate a conservative 48-hour irrigation recommendation.
Designed to support — not replace — operator judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SOIL_THRESHOLDS = {
    "sand": {"dry": 0.12, "wet": 0.28},
    "loam": {"dry": 0.18, "wet": 0.35},
    "clay": {"dry": 0.22, "wet": 0.40},
}

DEFAULT_COST_PER_IN_ACRE = 82.25  # $/in/acre (converted from $8/mm/ha)


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
    sensor_penalty = 0.0 if inputs.sensor_count >= 4 else 0.08
    timing_penalty = 0.05 if timing_window == "next available permitted window" else 0.0
    confidence = base + margin_bonus - sensor_penalty - timing_penalty
    return round(min(0.99, max(0.05, confidence)), 3)


def generate_irrigation_plan(inputs: OptimizationInputs) -> dict[str, Any]:
    thresholds = SOIL_THRESHOLDS.get(inputs.soil_texture, SOIL_THRESHOLDS["loam"])
    dry_threshold = thresholds["dry"]
    wet_threshold = thresholds["wet"]
    predicted_48h = inputs.predicted_moisture["moisture_48h"]
    needs_water = predicted_48h < dry_threshold

    timing_window = _select_timing_window(
        water_rights_schedule=inputs.water_rights_schedule,
        energy_price_window=inputs.energy_price_window,
        needs_water=needs_water,
    )

    target_moisture = min(wet_threshold, dry_threshold + 0.08 + inputs.estimated_et_in * 0.0508)
    deficit = max(0.0, target_moisture - predicted_48h)
    root_zone_factor = {"sand": 4.331, "loam": 5.315, "clay": 6.102}.get(inputs.soil_texture, 5.315)
    raw_amount_in = deficit * root_zone_factor
    precip_adjustment = max(0.0, inputs.recent_precipitation_in * 0.7)
    raw_amount_in = max(0.0, raw_amount_in - precip_adjustment)

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

    confidence = _confidence_score(inputs, dry_threshold=dry_threshold, timing_window=timing_window)
    return {
        "decision": "water" if needs_water else "wait",
        "recommended_amount_in": round(max(0.0, recommended_amount), 2),
        "timing_window": timing_window,
        "confidence_score": confidence,
        "soil_dry_threshold": dry_threshold,
        "soil_wet_threshold": wet_threshold,
    }
