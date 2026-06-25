# Helios Domain Glossary

The ubiquitous language for Helios. Names here are load-bearing: use them in code, tests,
docs, and architecture reviews. Architecture vocabulary (module, interface, depth, seam,
adapter, leverage, locality) comes from the `/codebase-design` skill, not this file.

## Agronomy module

The single deep module that owns the soil-water physics and the agronomic constants that
drive it. Lives at `helios/agronomy/`. It is a **dependency-free leaf**: it imports nothing
from the rest of `helios`, takes primitives (floats/strings) in and out, and is imported by
the parsers (`scripts/`), the optimizer, the feature pipeline (`data/`), and the
recommendation service. Before this module existed, its contents were copied across
`training_shared.py`, `mickelson_support.py`, `generate_sample_data.py`, and
`irrigation_optimizer.py`.

Public surface:

- **Forward step** — `step_forward(...)`: the daily soil-water balance. Given a moisture
  state, reference ET, precipitation, and irrigation, returns the next-day volumetric
  moisture (raw, unclamped). Used to **generate training targets**. Callers apply their own
  clamp bounds and any sampling noise — those are sampling policy, not physics.
- **Inverse kernels** — `target_moisture(...)` and `gross_application_in(...)`: convert a
  forecast moisture deficit into a conservative irrigation depth. Used by the optimizer. The
  optimizer keeps its own caps (pump, budget, infiltration), decision, timing, and confidence
  logic — only the physics moves.
- **Policy** — `stress_probability(...)` and `drivers(...)`: the stress and
  human-readable-driver heuristics, relocated out of `RecommendationService`.

## Soil-water balance

The FAO-56-style daily water balance Helios uses for both directions:
`Δmoisture = −et_depletion + precip_gain + irrigation_gain`, each term divided by a root-zone
depth. The **forward** direction simulates moisture to make training targets; the **inverse**
direction sizes an irrigation application. The two directions are *not* mathematical inverses
of each other by design — see depletion vs refill depth.

## Depletion depth vs Refill depth

Two **intentionally different** root-zone depths. Their ~0.3 ratio is a deliberate agronomic
choice, **not a bug** — do not "reconcile" them.

- **`ROOT_ZONE_DEPTH_IN`** (depletion depth) — the full root profile (≈300–500 mm). Used in
  the **forward** balance for ET depletion and recharge.
- **`REFILL_DEPTH_IN`** (refill depth) — the managed top fraction that an irrigation pass
  targets (≈110–155 mm, ≈0.3 × root depth). Used in the **inverse** application sizing. The
  smaller depth makes recommendations deliberately **conservative** ("support, not replace,
  operator judgment") and is consistent with a Management Allowable Depletion (MAD) refill
  target. Changing it would shift every recommendation ~3.3× and requires field re-validation
  (the Kimberly harness) before it could be trusted — out of scope for the consolidation.

## Behavior-preserving consolidation

The mandate for the agronomy refactor: centralize the constants and dedupe the formulas while
producing **byte-for-byte identical outputs**. No retrain of the model artifact, no field
re-validation. Proven by golden-master tests on the pure kernels (captured before the move,
asserted after).
