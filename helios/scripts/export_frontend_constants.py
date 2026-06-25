"""Generate the browser demo's shared agronomic constants from the Python source of truth.

The demo (src/domain/recommendations.js) must agree with the backend. Rather than hand-copy
the constant tables into JavaScript — where they drift — we emit them from helios.agronomy
(plus the optimizer's cost constant) into a committed, machine-owned file:
src/generated/agronomy-constants.js.

Run:    python3 -m helios.scripts.export_frontend_constants
Guard:  tests/test_frontend_constants_generated.py (regenerate-and-diff; fails on drift)
"""

from __future__ import annotations

from pathlib import Path

from helios import agronomy
from helios.optimizer.irrigation_optimizer import DEFAULT_COST_PER_IN_ACRE

OUTPUT_PATH = Path("src/generated/agronomy-constants.js")

HEADER = """\
// ─────────────────────────────────────────────────────────────────────────────
// GENERATED FILE — DO NOT EDIT BY HAND.
// Source of truth: helios/agronomy (+ helios.optimizer DEFAULT_COST_PER_IN_ACRE).
// Regenerate: python3 -m helios.scripts.export_frontend_constants
// Drift guard: tests/test_frontend_constants_generated.py
// Demo/backend formula parity guard: tests/test_demo_backend_parity.py
// ─────────────────────────────────────────────────────────────────────────────
"""


def _num(value: float) -> str:
    # repr() gives the shortest round-tripping decimal — deterministic across runs.
    return repr(float(value))


def _flat(name: str, table: dict[str, float], comment: str = "") -> str:
    body = ", ".join(f'"{k}": {_num(v)}' for k, v in table.items())
    suffix = f"  // {comment}" if comment else ""
    return f"export const {name} = {{ {body} }};{suffix}"


def _nested(name: str, table: dict[str, dict[str, float]]) -> str:
    rows = ", ".join(
        f'"{k}": {{ ' + ", ".join(f'"{ik}": {_num(iv)}' for ik, iv in inner.items()) + " }"
        for k, inner in table.items()
    )
    return f"export const {name} = {{ {rows} }};"


def render() -> str:
    lines = [
        HEADER,
        _nested("SOIL_THRESHOLDS", agronomy.SOIL_THRESHOLDS),
        # JS keeps the name ROOT_ZONE_FACTORS; the Python source is REFILL_DEPTH_IN
        # (the conservative managed-refill depth, not the full root-zone depletion depth).
        _flat("ROOT_ZONE_FACTORS", agronomy.REFILL_DEPTH_IN, "Python REFILL_DEPTH_IN"),
        _flat("IRRIGATION_EFFICIENCY", agronomy.IRRIGATION_EFFICIENCY),
        _flat("GROWTH_STAGE_MODIFIER", agronomy.GROWTH_STAGE_MODIFIER),
        _flat("DRAINAGE_FACTOR", agronomy.DRAINAGE_FACTOR),
        _flat("CROP_KC", agronomy.CROP_KC),
        f"export const COST_PER_IN_ACRE = {_num(DEFAULT_COST_PER_IN_ACRE)};",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    output = OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render())
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
