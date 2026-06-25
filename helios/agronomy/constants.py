"""Agronomic constants for the Helios soil-water balance.

Single home for the constant tables that drive both directions of the water balance:
the forward step (training-target generation) and the inverse application sizing
(the irrigation optimizer). See CONTEXT.md → "Agronomy module".
"""

from __future__ import annotations

# Growth-stage crop coefficient (Kc), FAO-56 style. Scales ET demand by stage.
CROP_KC = {
    "emergence": 0.3,
    "vegetative": 0.7,
    "flowering": 1.15,
    "grain_fill": 1.0,
    "maturity": 0.5,
}

# Depletion depth: the full root profile (~300-500 mm). Used by the FORWARD water
# balance for ET depletion and recharge. Intentionally different from REFILL_DEPTH_IN
# below — do not reconcile the two; the ~3.3x gap is a deliberate agronomic choice.
ROOT_ZONE_DEPTH_IN = {
    "sand": 11.811,
    "loam": 17.717,
    "clay": 19.685,
}

# Refill depth: the managed top fraction (~110-155 mm, ~0.3 x root depth) that a single
# conservative irrigation pass targets. Used by the INVERSE application sizing in the
# optimizer. The smaller depth makes recommendations deliberately conservative
# (Management Allowable Depletion / "support, not replace, operator judgment"). Changing
# it shifts every recommendation ~3.3x and requires field re-validation. See
# ROOT_ZONE_DEPTH_IN and CONTEXT.md → "Depletion depth vs Refill depth".
REFILL_DEPTH_IN = {
    "sand": 4.331,
    "loam": 5.315,
    "clay": 6.102,
}

# Drainage multiplier on ET depletion / gross application. Well-drained soils shed
# faster and need a larger gross application than poorly drained ones.
DRAINAGE_FACTOR = {
    "poor": 0.75,
    "moderate": 1.0,
    "well": 1.15,
}

IRRIGATION_EFFICIENCY = {
    "pivot": 0.82,
    "drip": 0.93,
    "flood": 0.68,
}

# Volumetric moisture dry/wet bounds by soil texture.
SOIL_THRESHOLDS = {
    "sand": {"dry": 0.12, "wet": 0.28},
    "loam": {"dry": 0.18, "wet": 0.35},
    "clay": {"dry": 0.22, "wet": 0.40},
}

# Per-growth-stage additive bump to the stress-probability score.
GROWTH_STAGE_MODIFIER = {
    "emergence": 0.05,
    "vegetative": 0.1,
    "flowering": 0.18,
    "grain_fill": 0.14,
    "maturity": 0.02,
}

# Fraction of precipitation that enters the root zone (forward balance recharge term).
PRECIP_INFILTRATION_EFFICIENCY = 0.90

# Inverse application target-buffer literals: target = dry + TARGET_BUFFER_IN +
# et * kc * ET_BUFFER_FACTOR, capped at the wet threshold.
TARGET_BUFFER_IN = 0.08
ET_BUFFER_FACTOR = 0.0508
