"""Agronomic policy heuristics: water-stress probability and recommendation drivers.

Relocated out of RecommendationService so the backend and (eventually) the demo share
one tested interface. Pure functions over primitives.
"""

from __future__ import annotations

import math

from helios.agronomy.constants import GROWTH_STAGE_MODIFIER, SOIL_THRESHOLDS


def stress_probability(
    *,
    predicted_moisture_48h: float,
    dry_threshold: float,
    estimated_et_in: float,
    growth_stage: str,
) -> float:
    stage_modifier = GROWTH_STAGE_MODIFIER.get(growth_stage, 0.1)
    moisture_gap = dry_threshold - predicted_moisture_48h
    # Precipitation is already an input to the 48h moisture forecast, so it is not
    # subtracted again here — doing so would double-count the rain's drying offset.
    score = (moisture_gap * 18.0) + (estimated_et_in * 3.048) + stage_modifier
    probability = 1.0 / (1.0 + math.exp(-score))
    return round(min(0.99, max(0.01, probability)), 3)


def drivers(
    *,
    estimated_et_in: float,
    current_moisture: float,
    soil_texture: str,
    precipitation_in: float,
    water_rights_window_count: int,
    growth_stage: str,
    stress_probability: float,
    predicted_moisture_24h: float,
    predicted_moisture_72h: float,
) -> list[str]:
    result: list[str] = []
    if estimated_et_in >= 0.217:  # ~5.5 mm/day in inches
        result.append("high evapotranspiration")
    if current_moisture <= SOIL_THRESHOLDS[soil_texture]["dry"] + 0.04:
        result.append("low soil moisture")
    if precipitation_in < 0.059:  # ~1.5 mm in inches
        result.append("limited forecast precipitation")
    if water_rights_window_count <= 1:
        result.append("restrictive water rights window")
    if growth_stage in {"flowering", "grain_fill"}:
        result.append("sensitive crop growth stage")
    if stress_probability > 0.8 and predicted_moisture_72h < predicted_moisture_24h:
        result.append("continued drying trend")
    return result[:3] or ["stable near-threshold moisture"]
