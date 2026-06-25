// ─────────────────────────────────────────────────────────────────────────────
// GENERATED FILE — DO NOT EDIT BY HAND.
// Source of truth: helios/agronomy (+ helios.optimizer DEFAULT_COST_PER_IN_ACRE).
// Regenerate: python3 -m helios.scripts.export_frontend_constants
// Drift guard: tests/test_frontend_constants_generated.py
// Demo/backend formula parity guard: tests/test_demo_backend_parity.py
// ─────────────────────────────────────────────────────────────────────────────

export const SOIL_THRESHOLDS = { "sand": { "dry": 0.12, "wet": 0.28 }, "loam": { "dry": 0.18, "wet": 0.35 }, "clay": { "dry": 0.22, "wet": 0.4 } };
export const ROOT_ZONE_FACTORS = { "sand": 4.331, "loam": 5.315, "clay": 6.102 };  // Python REFILL_DEPTH_IN
export const IRRIGATION_EFFICIENCY = { "pivot": 0.82, "drip": 0.93, "flood": 0.68 };
export const GROWTH_STAGE_MODIFIER = { "emergence": 0.05, "vegetative": 0.1, "flowering": 0.18, "grain_fill": 0.14, "maturity": 0.02 };
export const DRAINAGE_FACTOR = { "poor": 0.75, "moderate": 1.0, "well": 1.15 };
export const CROP_KC = { "emergence": 0.3, "vegetative": 0.7, "flowering": 1.15, "grain_fill": 1.0, "maturity": 0.5 };
export const COST_PER_IN_ACRE = 82.25;
