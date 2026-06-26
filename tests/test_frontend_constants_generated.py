"""Drift guard: the generated JS constants must stay in sync with helios.agronomy.

Pure Python, no JS runtime — always runs. Fails if anyone hand-edits the generated file
or changes the Python constants without regenerating.
"""

from __future__ import annotations

from pathlib import Path

from helios.scripts.export_frontend_constants import render

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED = REPO_ROOT / "src" / "generated" / "agronomy-constants.js"


def test_generated_frontend_constants_in_sync():
    committed = GENERATED.read_text()
    assert committed == render(), (
        "src/generated/agronomy-constants.js is stale. "
        "Run: python3 -m helios.scripts.export_frontend_constants"
    )
