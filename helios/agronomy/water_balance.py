"""Soil-water balance: the forward daily step and the inverse application kernels.

The forward step generates training targets; the inverse kernels size an irrigation
application for the optimizer. They are NOT mathematical inverses of each other by
design — the forward step uses ROOT_ZONE_DEPTH_IN (depletion), the inverse uses
REFILL_DEPTH_IN (conservative refill). See CONTEXT.md.
"""

from __future__ import annotations

from helios.agronomy.constants import (
    CROP_KC,
    DRAINAGE_FACTOR,
    ET_BUFFER_FACTOR,
    IRRIGATION_EFFICIENCY,
    PRECIP_INFILTRATION_EFFICIENCY,
    REFILL_DEPTH_IN,
    ROOT_ZONE_DEPTH_IN,
    TARGET_BUFFER_IN,
)


def step_forward(
    moisture: float,
    *,
    reference_et_in: float,
    precip_in: float,
    irrigation_in: float,
    growth_stage: str,
    soil_texture: str,
    drainage_class: str,
    irrigation_type: str,
) -> float:
    """Advance volumetric soil moisture one day. Returns the raw next value.

    Callers apply their own clamp bounds and any sampling noise — those are sampling
    policy, not physics.
    """
    kc = CROP_KC[growth_stage]
    root_depth = ROOT_ZONE_DEPTH_IN[soil_texture]
    drainage = DRAINAGE_FACTOR[drainage_class]
    efficiency = IRRIGATION_EFFICIENCY[irrigation_type]
    et_depletion = (reference_et_in * kc * drainage) / root_depth
    precip_gain = precip_in * PRECIP_INFILTRATION_EFFICIENCY / root_depth
    irrigation_gain = irrigation_in * efficiency / root_depth
    return moisture - et_depletion + precip_gain + irrigation_gain


def target_moisture(
    *,
    dry_threshold: float,
    wet_threshold: float,
    estimated_et_in: float,
    growth_stage: str,
) -> float:
    """Inverse: the moisture level a conservative application aims to reach."""
    crop_kc = CROP_KC.get(growth_stage, 1.0)
    return min(
        wet_threshold,
        dry_threshold + TARGET_BUFFER_IN + estimated_et_in * crop_kc * ET_BUFFER_FACTOR,
    )


def gross_application_in(
    *,
    deficit: float,
    soil_texture: str,
    drainage_class: str,
    irrigation_type: str,
) -> float:
    """Inverse: gross irrigation depth (inches) to close a moisture deficit.

    Uses REFILL_DEPTH_IN, not ROOT_ZONE_DEPTH_IN — the conservative managed-refill depth.
    """
    refill_depth = REFILL_DEPTH_IN.get(soil_texture, REFILL_DEPTH_IN["loam"])
    drainage_factor = DRAINAGE_FACTOR.get(drainage_class, 1.0)
    net_amount_in = deficit * refill_depth * drainage_factor
    efficiency = IRRIGATION_EFFICIENCY.get(irrigation_type, IRRIGATION_EFFICIENCY["pivot"])
    return net_amount_in / efficiency
