from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_model_artifact_contract_passes_for_committed_artifacts() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "helios.scripts.check_model_artifact_contract"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "model artifact contract passed" in result.stdout


def test_model_artifact_contract_reports_missing_required_metadata(tmp_path: Path) -> None:
    metadata_path = tmp_path / "model_metadata.json"
    metadata_path.write_text(json.dumps({"model_hash": "abc123"}))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "helios.scripts.check_model_artifact_contract",
            "--metadata-path",
            str(metadata_path),
            "--model-path",
            str(tmp_path / "missing.pkl"),
            "--eval-path",
            str(tmp_path / "missing-eval.json"),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing required metadata field: training_rows" in result.stderr
    assert "missing required metadata field: feature_importances" in result.stderr
