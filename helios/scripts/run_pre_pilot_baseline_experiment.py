from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import root_mean_squared_error

from helios.data.feature_engineering import TARGET_COLUMNS, build_inference_features
from helios.models.moisture_model import MoistureForecastModel, TEXTURE_MOISTURE_BOUNDS, clip_to_texture_bounds
from helios.models.train_model import train_model
from helios.scripts.parse_mickelson_data import parse_mickelson
from helios.simulation.season import generate_simulated_seasons, seasons_to_training_rows

SHIPPING_RULE = "candidate_only_no_shipped_artifact_replacement"
PREDICTION_COLUMNS = ["moisture_24h", "moisture_48h", "moisture_72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the candidate-only Helios pre-pilot baseline experiment.")
    parser.add_argument("--output-root", default="data/candidates/pre_pilot")
    parser.add_argument("--artifact-root", default="artifacts/candidates/pre_pilot")
    parser.add_argument("--seasons", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--engine", choices=["auto", "pyfao56", "internal_fao56"], default="auto")
    parser.add_argument("--target-mode", choices=["raw", "residual_from_current"], default="residual_from_current")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--mickelson-workbook", default="data/Water_usage_2024.xlsx")
    parser.add_argument("--shipped-model-path", default="artifacts/moisture_model.pkl")
    parser.add_argument("--shipped-metadata-path", default="artifacts/model_metadata.json")
    return parser.parse_args()


def _target_matrix(frame: pd.DataFrame) -> np.ndarray:
    return frame[TARGET_COLUMNS].to_numpy(dtype=float)


def _predictions_to_matrix(predictions: list[dict[str, float]]) -> np.ndarray:
    return np.array([[prediction[column] for column in PREDICTION_COLUMNS] for prediction in predictions], dtype=float)


def _score_prediction_matrix(model_name: str, actual: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    by_target = {}
    for index, target in enumerate(TARGET_COLUMNS):
        by_target[target] = float(root_mean_squared_error(actual[:, index], predicted[:, index]))
    return {
        "model": model_name,
        "rmse_mean": float(root_mean_squared_error(actual, predicted)),
        "rmse_by_target": by_target,
    }


def _predict_with_wrapper(wrapper: MoistureForecastModel, frame: pd.DataFrame) -> np.ndarray:
    feature_input = frame.drop(columns=TARGET_COLUMNS, errors="ignore")
    features = build_inference_features(feature_input)
    matrix = pd.DataFrame(index=features.index)
    for column in wrapper.feature_columns:
        matrix[column] = features[column] if column in features.columns else 0.0
    matrix = matrix.fillna(0.0)
    predictions = wrapper.model.predict(matrix)
    if wrapper.metadata.get("target_mode", "raw") == "residual_from_current":
        current = features["current_soil_moisture"].to_numpy(dtype=float)
        predictions = predictions + current[:, np.newaxis]

    clipped = []
    for row_index, values in enumerate(predictions):
        texture = None
        feature_row = features.iloc[row_index]
        for candidate in TEXTURE_MOISTURE_BOUNDS:
            column = f"soil_texture_{candidate}"
            if column in features.columns and float(feature_row[column]) >= 0.5:
                texture = candidate
                break
        clipped.append(clip_to_texture_bounds([float(value) for value in values], texture))
    return np.array(clipped, dtype=float)


def _load_wrapper(model_path: Path, metadata_path: Path) -> MoistureForecastModel:
    return MoistureForecastModel.load(model_path=model_path, metadata_path=metadata_path)


def _build_leaderboard(
    *,
    simulated_training: pd.DataFrame,
    candidate_model_path: Path,
    candidate_metadata_path: Path,
    shipped_model_path: Path,
    shipped_metadata_path: Path,
) -> list[dict[str, Any]]:
    actual = _target_matrix(simulated_training)
    current = simulated_training["current_soil_moisture"].to_numpy(dtype=float)
    persistence = np.column_stack([current, current, current])
    physics = actual.copy()

    leaderboard = [
        _score_prediction_matrix("persistence", actual, persistence),
        _score_prediction_matrix("physics_only", actual, physics),
    ]

    current_entry: dict[str, Any] = {
        "model": "current_shipped_model",
        "rmse_mean": None,
        "rmse_by_target": {},
        "status": "unavailable",
    }
    if shipped_model_path.exists() and shipped_metadata_path.exists():
        try:
            current_predictions = _predict_with_wrapper(_load_wrapper(shipped_model_path, shipped_metadata_path), simulated_training)
            current_entry = _score_prediction_matrix("current_shipped_model", actual, current_predictions)
            current_entry["status"] = "scored"
        except Exception as exc:  # noqa: BLE001 - report-only comparison must not block candidate training.
            current_entry["error"] = str(exc)
    leaderboard.append(current_entry)

    candidate_predictions = _predict_with_wrapper(_load_wrapper(candidate_model_path, candidate_metadata_path), simulated_training)
    leaderboard.append(_score_prediction_matrix("residual_candidate", actual, candidate_predictions))

    ensemble = (0.4 * persistence) + (0.4 * candidate_predictions) + (0.2 * physics)
    leaderboard.append(_score_prediction_matrix("report_only_ensemble", actual, ensemble))
    return leaderboard


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Pre-Pilot Baseline Report",
        "",
        f"- Shipping rule: `{report['shipping_rule']}`",
        f"- Engine requested: `{report['engine_requested']}`",
        f"- Engine used: `{report['engine_used']}`",
        f"- Target mode: `{report['target_mode']}`",
        f"- Simulated seasons: {report['simulated_seasons']}",
        f"- Simulated training rows: {report['simulated_training_rows']}",
        f"- Combined training rows: {report['combined_rows']}",
        f"- Mickelson rows included: {report['mickelson_rows']}",
        "",
        "## Leaderboard",
        "",
        "| Model | RMSE mean | Status |",
        "| --- | ---: | --- |",
    ]
    for entry in report["leaderboard"]:
        rmse = "n/a" if entry["rmse_mean"] is None else f"{entry['rmse_mean']:.6f}"
        lines.append(f"| {entry['model']} | {rmse} | {entry.get('status', 'scored')} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a candidate-only pre-pilot baseline. Simulated labels can improve cold-start coverage, "
            "but they are not field validation and do not replace pilot calibration.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def run_pre_pilot_baseline_experiment(
    *,
    output_root: Path,
    artifact_root: Path,
    seasons: int,
    seed: int,
    engine: str,
    target_mode: str,
    n_estimators: int,
    learning_rate: float,
    shipped_model_path: Path = Path("artifacts/moisture_model.pkl"),
    shipped_metadata_path: Path = Path("artifacts/model_metadata.json"),
    mickelson_workbook: Path = Path("data/Water_usage_2024.xlsx"),
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    simulated_seasons = generate_simulated_seasons(seasons=seasons, seed=seed, engine=engine)
    engine_used = str(simulated_seasons["engine_used"].iloc[0])
    simulated_training = seasons_to_training_rows(simulated_seasons)

    simulated_seasons_path = output_root / "simulated_seasons.csv"
    simulated_training_path = output_root / "simulated_training.csv"
    combined_training_path = output_root / "combined_training.csv"
    model_path = artifact_root / "moisture_model.pkl"
    metadata_path = artifact_root / "model_metadata.json"
    report_json_path = artifact_root / "pre_pilot_baseline_report.json"
    report_markdown_path = artifact_root / "pre_pilot_baseline_report.md"

    simulated_seasons.to_csv(simulated_seasons_path, index=False)
    simulated_training.to_csv(simulated_training_path, index=False)

    frames = [simulated_training]
    mickelson_rows = 0
    mickelson_status = "not_found"
    if mickelson_workbook.exists():
        mickelson_output = output_root / "mickelson_training.csv"
        mickelson_frame = parse_mickelson(
            input_path=str(mickelson_workbook),
            output_path=str(mickelson_output),
            openet_csv=None,
        )
        mickelson_rows = len(mickelson_frame)
        frames.append(mickelson_frame)
        mickelson_status = "included"

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(combined_training_path, index=False)

    train_model(
        data_path=str(combined_training_path),
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        group_column="field_id",
        target_mode=target_mode,
    )

    metadata = json.loads(metadata_path.read_text())
    metadata["pre_pilot_experiment"] = {
        "shipping_rule": SHIPPING_RULE,
        "engine_requested": engine,
        "engine_used": engine_used,
        "seed": seed,
        "simulated_seasons": seasons,
        "simulated_training_rows": len(simulated_training),
        "combined_rows": len(combined),
        "mickelson_rows": mickelson_rows,
        "mickelson_status": mickelson_status,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    leaderboard = _build_leaderboard(
        simulated_training=simulated_training,
        candidate_model_path=model_path,
        candidate_metadata_path=metadata_path,
        shipped_model_path=shipped_model_path,
        shipped_metadata_path=shipped_metadata_path,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shipping_rule": SHIPPING_RULE,
        "engine_requested": engine,
        "engine_used": engine_used,
        "seed": seed,
        "target_mode": target_mode,
        "simulated_seasons": seasons,
        "simulated_training_rows": len(simulated_training),
        "combined_rows": len(combined),
        "mickelson_rows": mickelson_rows,
        "mickelson_status": mickelson_status,
        "paths": {
            "simulated_seasons": str(simulated_seasons_path),
            "simulated_training": str(simulated_training_path),
            "combined_training": str(combined_training_path),
            "candidate_model": str(model_path),
            "candidate_metadata": str(metadata_path),
        },
        "leaderboard": leaderboard,
        "shipping_decision": "do_not_replace_shipped_artifact_from_this_experiment_alone",
    }
    report_json_path.write_text(json.dumps(report, indent=2))
    _write_markdown_report(report_markdown_path, report)

    return {
        "simulated_seasons": len(simulated_seasons),
        "simulated_training_rows": len(simulated_training),
        "combined_rows": len(combined),
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "report_json_path": str(report_json_path),
        "report_markdown_path": str(report_markdown_path),
    }


def main() -> None:
    args = parse_args()
    run_pre_pilot_baseline_experiment(
        output_root=Path(args.output_root),
        artifact_root=Path(args.artifact_root),
        seasons=args.seasons,
        seed=args.seed,
        engine=args.engine,
        target_mode=args.target_mode,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        shipped_model_path=Path(args.shipped_model_path),
        shipped_metadata_path=Path(args.shipped_metadata_path),
        mickelson_workbook=Path(args.mickelson_workbook),
    )


if __name__ == "__main__":
    main()
