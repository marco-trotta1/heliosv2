"""Helios agronomy: the deep module for the soil-water balance and its constants.

A dependency-free leaf — imports nothing from the rest of ``helios``. Parsers, the
optimizer, the feature pipeline, and the recommendation service all call through it.
See CONTEXT.md → "Agronomy module".
"""

from __future__ import annotations

from helios.agronomy.constants import (
    CROP_KC,
    DRAINAGE_FACTOR,
    ET_BUFFER_FACTOR,
    GROWTH_STAGE_MODIFIER,
    IRRIGATION_EFFICIENCY,
    PRECIP_INFILTRATION_EFFICIENCY,
    REFILL_DEPTH_IN,
    ROOT_ZONE_DEPTH_IN,
    SOIL_THRESHOLDS,
    TARGET_BUFFER_IN,
)
from helios.agronomy.policy import drivers, stress_probability
from helios.agronomy.water_balance import (
    gross_application_in,
    step_forward,
    target_moisture,
)

__all__ = [
    "CROP_KC",
    "DRAINAGE_FACTOR",
    "ET_BUFFER_FACTOR",
    "GROWTH_STAGE_MODIFIER",
    "IRRIGATION_EFFICIENCY",
    "PRECIP_INFILTRATION_EFFICIENCY",
    "REFILL_DEPTH_IN",
    "ROOT_ZONE_DEPTH_IN",
    "SOIL_THRESHOLDS",
    "TARGET_BUFFER_IN",
    "drivers",
    "gross_application_in",
    "step_forward",
    "stress_probability",
    "target_moisture",
]
