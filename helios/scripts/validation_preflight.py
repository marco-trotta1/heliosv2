from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from helios.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit a frozen validation manifest for a farm test run.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the JSON manifest. Defaults to stdout only.",
    )
    return parser.parse_args()


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def build_manifest() -> dict[str, Any]:
    settings = get_settings()
    metadata = _load_metadata(settings.metadata_path)
    model_hash = _sha256(settings.model_path)
    metadata_hash = _sha256(settings.metadata_path)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "validation_mode": settings.validation_mode,
        "model_path": str(settings.model_path),
        "metadata_path": str(settings.metadata_path),
        "model_exists": settings.model_path.exists(),
        "metadata_exists": settings.metadata_path.exists(),
        "model_hash": model_hash,
        "metadata_hash": metadata_hash,
        "training_date": metadata.get("training_date") or metadata.get("trained_at"),
        "training_rows": metadata.get("training_rows"),
        "cv_rmse_mean": metadata.get("cv_rmse_mean"),
        "validation_rmse": metadata.get("validation_rmse"),
        "training_data_hash": metadata.get("training_data_hash"),
        "checks": {
            "model_artifact_present": settings.model_path.exists(),
            "metadata_present": settings.metadata_path.exists(),
            "validation_mode_enabled": settings.validation_mode,
        },
    }


def main() -> None:
    args = parse_args()
    manifest = build_manifest()
    serialized = json.dumps(manifest, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
