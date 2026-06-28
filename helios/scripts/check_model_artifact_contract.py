from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib


DEFAULT_MODEL_PATH = Path("artifacts/moisture_model.pkl")
DEFAULT_METADATA_PATH = Path("artifacts/model_metadata.json")
DEFAULT_EVAL_PATH = Path("artifacts/maize_baseline_eval.json")

REQUIRED_METADATA_FIELDS = (
    "model_hash",
    "training_data_hash",
    "training_rows",
    "feature_columns",
    "target_columns",
    "cv_rmse_mean",
    "cv_rmse_by_target",
    "feature_importances",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _training_date(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("training_date") or metadata.get("trained_at")
    return value if isinstance(value, str) and value.strip() else None


def _has_cv_metrics(metadata: dict[str, Any]) -> bool:
    return isinstance(metadata.get("cv_rmse_mean"), int | float) and isinstance(
        metadata.get("cv_rmse_by_target"),
        dict,
    )


def _derive_feature_importances(model_path: Path, metadata: dict[str, Any]) -> dict[str, dict[str, float]] | None:
    if not model_path.exists():
        return None

    feature_columns = metadata.get("feature_columns")
    target_columns = metadata.get("target_columns")
    if not isinstance(feature_columns, list) or not all(isinstance(item, str) for item in feature_columns):
        return None
    if not isinstance(target_columns, list) or not all(isinstance(item, str) for item in target_columns):
        return None

    model = joblib.load(model_path)
    estimators = getattr(model, "estimators_", None)
    if not isinstance(estimators, list) or len(estimators) != len(target_columns):
        return None

    importances: dict[str, dict[str, float]] = {}
    for target_name, estimator in zip(target_columns, estimators, strict=True):
        scores = getattr(estimator, "feature_importances_", None)
        if scores is None or len(scores) != len(feature_columns):
            return None
        ranked = sorted(
            zip(feature_columns, [float(score) for score in scores], strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        importances[target_name] = {name: round(score, 6) for name, score in ranked}
    return importances


def _validate_metadata(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in REQUIRED_METADATA_FIELDS:
        if field_name not in metadata:
            errors.append(f"missing required metadata field: {field_name}")

    if _training_date(metadata) is None:
        errors.append("missing required metadata field: training_date")
    if not _has_cv_metrics(metadata):
        errors.append("metadata must include cv_rmse_mean and cv_rmse_by_target")
    if not isinstance(metadata.get("feature_columns"), list) or not metadata.get("feature_columns"):
        errors.append("feature_columns must be a non-empty list")
    if not isinstance(metadata.get("target_columns"), list) or not metadata.get("target_columns"):
        errors.append("target_columns must be a non-empty list")
    if not isinstance(metadata.get("training_rows"), int) or metadata.get("training_rows", 0) <= 0:
        errors.append("training_rows must be a positive integer")
    if not isinstance(metadata.get("feature_importances"), dict) or not metadata.get("feature_importances"):
        errors.append("feature_importances must be a non-empty object")
    return errors


def check_contract(
    *,
    model_path: Path,
    metadata_path: Path,
    eval_path: Path,
    write_metadata: bool,
) -> list[str]:
    errors: list[str] = []
    if not metadata_path.exists():
        return [f"metadata artifact missing: {metadata_path}"]

    metadata = _load_json(metadata_path)
    if "feature_importances" not in metadata:
        derived = _derive_feature_importances(model_path, metadata)
        if derived is not None and write_metadata:
            metadata["feature_importances"] = derived
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    errors.extend(_validate_metadata(metadata))

    if not model_path.exists():
        errors.append(f"model artifact missing: {model_path}")
    if eval_path.exists():
        evaluation = _load_json(eval_path)
        verdict = evaluation.get("verdict")
        if not isinstance(verdict, str) or not verdict:
            errors.append(f"evaluation artifact missing verdict: {eval_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate committed Helios model artifact metadata.")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metadata-path", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument(
        "--write-metadata",
        action="store_true",
        help="Backfill derivable metadata fields without changing the model artifact.",
    )
    args = parser.parse_args()

    try:
        errors = check_contract(
            model_path=args.model_path,
            metadata_path=args.metadata_path,
            eval_path=args.eval_path,
            write_metadata=args.write_metadata,
        )
    except Exception as exc:
        print(f"model artifact contract failed: {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("model artifact contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
