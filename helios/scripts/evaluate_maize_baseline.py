from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from helios.data.feature_engineering import build_training_features, prepare_feature_matrix
from helios.models.moisture_model import MoistureForecastModel
from helios.models.train_model import _build_cross_validation_splits, _fit_final_model
from helios.scripts.download_public_datasets import find_dataset, load_registry
from helios.scripts.score_validation_results import MAX_ABS_BIAS, MAX_MAE, VALID_VWC_MAX, VALID_VWC_MIN


HORIZON_KEYS = {
    "24h": ("target_moisture_24h", "target_source_24h", "moisture_24h"),
    "48h": ("target_moisture_48h", "target_source_48h", "moisture_48h"),
    "72h": ("target_moisture_72h", "target_source_72h", "moisture_72h"),
}
NO_REGRESSION_TOLERANCE_RMSE = 0.002


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate USDA maize as a Helios training candidate.")
    parser.add_argument("--base-csv", required=True)
    parser.add_argument("--maize-csv", required=True)
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--out-json", default="artifacts/maize_baseline_eval.json")
    parser.add_argument("--out-md", default="artifacts/maize_baseline_eval.md")
    return parser.parse_args()


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _registry_md5s() -> dict[str, str]:
    try:
        dataset = find_dataset(load_registry(), "usda_lirf_2012_2013")
    except KeyError:
        return {}
    return {
        str(file_info["name"]): str(file_info["md5"])
        for file_info in dataset.get("raw_files", [])
        if "md5" in file_info
    }


def _fit_model(frame: pd.DataFrame, *, n_estimators: int, learning_rate: float) -> MoistureForecastModel:
    features, targets = build_training_features(frame)
    feature_columns = list(features.columns)
    matrix = prepare_feature_matrix(features, feature_columns)
    groups = frame["field_id"] if "field_id" in frame.columns else None
    model = _fit_final_model(matrix, targets, n_estimators, learning_rate, groups=groups)
    return MoistureForecastModel(model=model, feature_columns=feature_columns, metadata={})


def _predict_frame(model: MoistureForecastModel, frame: pd.DataFrame) -> pd.DataFrame:
    features, _ = build_training_features(frame)
    predictions: list[dict[str, float]] = []
    for index in features.index:
        predictions.append(model.predict(features.loc[[index]]))
    return pd.DataFrame(predictions, index=frame.index)


def _empty_metrics() -> dict[str, float | int | bool]:
    return {
        "count": 0,
        "baseline_mae": 0.0,
        "candidate_mae": 0.0,
        "baseline_bias": 0.0,
        "candidate_bias": 0.0,
        "baseline_rmse": 0.0,
        "candidate_rmse": 0.0,
        "delta_mae": 0.0,
        "persistence_mae": 0.0,
        "candidate_beats_persistence": False,
    }


def _metric_summary(records: list[dict[str, Any]], *, measured_only: bool) -> dict[str, dict[str, float | int | bool]]:
    summary: dict[str, dict[str, float | int | bool]] = {}
    for horizon, (_, _, prediction_key) in HORIZON_KEYS.items():
        subset = [
            record for record in records
            if record["horizon"] == horizon and (not measured_only or record["target_source"] == "root_zone_weighted_swc")
        ]
        if not subset:
            summary[horizon] = _empty_metrics()
            continue

        baseline_errors = [float(record["baseline_prediction"] - record["observed"]) for record in subset]
        candidate_errors = [float(record["candidate_prediction"] - record["observed"]) for record in subset]
        persistence_errors = [float(record["current_soil_moisture"] - record["observed"]) for record in subset]
        baseline_mae = sum(abs(value) for value in baseline_errors) / len(baseline_errors)
        candidate_mae = sum(abs(value) for value in candidate_errors) / len(candidate_errors)
        persistence_mae = sum(abs(value) for value in persistence_errors) / len(persistence_errors)
        rounded_baseline_mae = round(baseline_mae, 6)
        rounded_candidate_mae = round(candidate_mae, 6)
        summary[horizon] = {
            "count": len(subset),
            "baseline_mae": rounded_baseline_mae,
            "candidate_mae": rounded_candidate_mae,
            "baseline_bias": round(sum(baseline_errors) / len(baseline_errors), 6),
            "candidate_bias": round(sum(candidate_errors) / len(candidate_errors), 6),
            "baseline_rmse": round(math.sqrt(sum(value * value for value in baseline_errors) / len(baseline_errors)), 6),
            "candidate_rmse": round(math.sqrt(sum(value * value for value in candidate_errors) / len(candidate_errors)), 6),
            "delta_mae": round(rounded_baseline_mae - rounded_candidate_mae, 6),
            "persistence_mae": round(persistence_mae, 6),
            "candidate_beats_persistence": candidate_mae < persistence_mae,
        }
    return summary


def _score_holdout(
    *,
    baseline_model: MoistureForecastModel,
    candidate_model: MoistureForecastModel,
    holdout: pd.DataFrame,
) -> list[dict[str, Any]]:
    baseline_predictions = _predict_frame(baseline_model, holdout)
    candidate_predictions = _predict_frame(candidate_model, holdout)
    rows: list[dict[str, Any]] = []
    for index, row in holdout.iterrows():
        for horizon, (target_column, source_column, prediction_key) in HORIZON_KEYS.items():
            rows.append(
                {
                    "horizon": horizon,
                    "target_source": row[source_column],
                    "observed": float(row[target_column]),
                    "current_soil_moisture": float(row["current_soil_moisture"]),
                    "baseline_prediction": float(baseline_predictions.loc[index, prediction_key]),
                    "candidate_prediction": float(candidate_predictions.loc[index, prediction_key]),
                }
            )
    return rows


def _protocol_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    measured = _metric_summary(records, measured_only=True)
    included = _metric_summary(records, measured_only=False)
    measured_threshold_pass = all(
        measured[horizon]["candidate_mae"] <= MAX_MAE
        and abs(float(measured[horizon]["candidate_bias"])) <= MAX_ABS_BIAS
        for horizon in ("48h", "72h")
        if measured[horizon]["count"] > 0
    )
    persistence_pass = all(
        bool(metrics["candidate_beats_persistence"])
        for metrics in measured.values()
        if metrics["count"] > 0
    )
    return {
        "summary": {
            "measured_only": measured,
            "interpolated_included": included,
        },
        "gates": {
            "measured_48h_count_nonzero": measured["48h"]["count"] > 0,
            "measured_72h_count_nonzero": measured["72h"]["count"] > 0,
            "measured_threshold_pass": measured_threshold_pass,
            "persistence_pass": persistence_pass,
        },
    }


def _evaluate_group_kfold(
    *,
    base: pd.DataFrame,
    maize: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> dict[str, Any]:
    baseline_model = _fit_model(base, n_estimators=n_estimators, learning_rate=learning_rate)
    records: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    splits = _build_cross_validation_splits(row_count=len(maize), groups=maize["field_id"])
    for train_idx, holdout_idx in splits:
        train_maize = maize.iloc[train_idx]
        holdout = maize.iloc[holdout_idx]
        candidate_model = _fit_model(
            pd.concat([base, train_maize], ignore_index=True),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        )
        fold_records = _score_holdout(
            baseline_model=baseline_model,
            candidate_model=candidate_model,
            holdout=holdout,
        )
        records.extend(fold_records)
        folds.append(
            {
                "train_groups": sorted(str(value) for value in train_maize["field_id"].unique()),
                "holdout_groups": sorted(str(value) for value in holdout["field_id"].unique()),
            }
        )
    result = _protocol_summary(records)
    result["folds"] = folds
    return result


def _evaluate_loyo(
    *,
    base: pd.DataFrame,
    maize: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> dict[str, Any]:
    maize = maize.copy()
    maize["_year"] = pd.to_datetime(maize["prediction_time"], errors="coerce").dt.year.astype(int)
    baseline_model = _fit_model(base, n_estimators=n_estimators, learning_rate=learning_rate)
    records: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for year in sorted(maize["_year"].dropna().unique()):
        train_maize = maize[maize["_year"] != year].drop(columns=["_year"])
        holdout = maize[maize["_year"] == year].drop(columns=["_year"])
        if train_maize.empty or holdout.empty:
            continue
        candidate_model = _fit_model(
            pd.concat([base, train_maize], ignore_index=True),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        )
        records.extend(
            _score_holdout(baseline_model=baseline_model, candidate_model=candidate_model, holdout=holdout)
        )
        folds.append(
            {
                "holdout_year": int(year),
                "train_groups": sorted(str(value) for value in train_maize["field_id"].unique()),
                "holdout_groups": sorted(str(value) for value in holdout["field_id"].unique()),
            }
        )
    result = _protocol_summary(records)
    result["folds"] = folds
    return result


def _rmse_on_frame(model: MoistureForecastModel, frame: pd.DataFrame) -> float:
    predictions = _predict_frame(model, frame)
    errors: list[float] = []
    for index, row in frame.iterrows():
        for _, (target_column, _, prediction_key) in HORIZON_KEYS.items():
            errors.append(float(predictions.loc[index, prediction_key]) - float(row[target_column]))
    return math.sqrt(sum(value * value for value in errors) / len(errors)) if errors else 0.0


def _base_no_regression(
    *,
    base: pd.DataFrame,
    maize: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> dict[str, Any]:
    baseline_scores: list[float] = []
    candidate_scores: list[float] = []
    folds: list[dict[str, Any]] = []
    for train_idx, holdout_idx in _build_cross_validation_splits(row_count=len(base), groups=base["field_id"]):
        train_base = base.iloc[train_idx]
        holdout = base.iloc[holdout_idx]
        baseline = _fit_model(train_base, n_estimators=n_estimators, learning_rate=learning_rate)
        candidate = _fit_model(
            pd.concat([train_base, maize], ignore_index=True),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        )
        baseline_scores.append(_rmse_on_frame(baseline, holdout))
        candidate_scores.append(_rmse_on_frame(candidate, holdout))
        folds.append(
            {
                "train_groups": sorted(str(value) for value in train_base["field_id"].unique()),
                "holdout_groups": sorted(str(value) for value in holdout["field_id"].unique()),
            }
        )
    baseline_mean = sum(baseline_scores) / len(baseline_scores)
    candidate_mean = sum(candidate_scores) / len(candidate_scores)
    return {
        "baseline_rmse_mean": round(baseline_mean, 6),
        "candidate_rmse_mean": round(candidate_mean, 6),
        "tolerance_rmse": NO_REGRESSION_TOLERANCE_RMSE,
        "pass": candidate_mean <= baseline_mean + NO_REGRESSION_TOLERANCE_RMSE,
        "folds": folds,
    }


def _transfer_proxy(
    *,
    base: pd.DataFrame,
    maize: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> dict[str, Any]:
    mickelson = base[base["source_id"] == "mickelson"] if "source_id" in base.columns else pd.DataFrame()
    if mickelson.empty or mickelson["field_id"].nunique() < 2:
        return {"status": "not_enough_mickelson_groups", "candidate_better": False}

    baseline_scores: list[float] = []
    candidate_scores: list[float] = []
    for train_idx, holdout_idx in _build_cross_validation_splits(row_count=len(mickelson), groups=mickelson["field_id"]):
        holdout_groups = set(mickelson.iloc[holdout_idx]["field_id"])
        train_base = base[~base["field_id"].isin(holdout_groups)]
        holdout = mickelson.iloc[holdout_idx]
        baseline = _fit_model(train_base, n_estimators=n_estimators, learning_rate=learning_rate)
        candidate = _fit_model(
            pd.concat([train_base, maize], ignore_index=True),
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        )
        baseline_scores.append(_rmse_on_frame(baseline, holdout))
        candidate_scores.append(_rmse_on_frame(candidate, holdout))
    baseline_mean = sum(baseline_scores) / len(baseline_scores)
    candidate_mean = sum(candidate_scores) / len(candidate_scores)
    return {
        "status": "scored",
        "baseline_rmse_mean": round(baseline_mean, 6),
        "candidate_rmse_mean": round(candidate_mean, 6),
        "candidate_better": candidate_mean < baseline_mean,
        "claim": "Idaho transfer unproven" if candidate_mean >= baseline_mean else "Mickelson holdout improved; Idaho transfer still requires field validation",
    }


def resolve_verdict(
    *,
    protocols: dict[str, Any],
    base_no_regression: dict[str, Any],
    transfer_proxy: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    for name, protocol in protocols.items():
        gates = protocol["gates"]
        if not gates.get("measured_48h_count_nonzero") or not gates.get("measured_72h_count_nonzero"):
            reasons.append(f"{name}: measured 48h/72h counts are required")
        if not gates.get("measured_threshold_pass"):
            reasons.append(f"{name}: measured MAE/bias thresholds failed")
        if not gates.get("persistence_pass"):
            reasons.append(f"{name}: candidate did not beat persistence")
    if not base_no_regression.get("pass"):
        reasons.append("base no-regression gate failed")
    if not transfer_proxy.get("candidate_better"):
        reasons.append("Mickelson transfer proxy did not improve")
    return ("CANDIDATE_FAIL" if reasons else "CANDIDATE_PASS", reasons)


def _write_markdown(path: str, result: dict[str, Any]) -> None:
    lines = [
        "# Maize Baseline Evaluation",
        "",
        f"Verdict: {result['verdict']}",
        "",
        "This evaluation is a candidate gate, not a validation claim.",
        "",
        "## Measured-Only Metrics",
        "",
        "| Protocol | Horizon | Count | Baseline MAE | Candidate MAE | Delta MAE | Persistence MAE | Candidate Bias | Candidate RMSE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for protocol_name in ("group_kfold", "loyo"):
        measured = result["protocols"][protocol_name]["summary"]["measured_only"]
        for horizon in ("24h", "48h", "72h"):
            metrics = measured[horizon]
            lines.append(
                "| {protocol} | {horizon} | {count} | {baseline_mae} | {candidate_mae} | {delta_mae} | "
                "{persistence_mae} | {candidate_bias} | {candidate_rmse} |".format(
                    protocol=protocol_name,
                    horizon=horizon,
                    **metrics,
                )
            )
    lines.extend(
        [
            "",
            "## Gates",
            "",
            f"- GroupKFold gates: `{json.dumps(result['protocols']['group_kfold']['gates'], sort_keys=True)}`",
            f"- LOYO gates: `{json.dumps(result['protocols']['loyo']['gates'], sort_keys=True)}`",
            "- Base no-regression: baseline RMSE `{baseline_rmse_mean}`, candidate RMSE `{candidate_rmse_mean}`, "
            "pass `{pass}`".format(**result["base_no_regression"]),
            f"- Transfer proxy: `{json.dumps(result['transfer_proxy'], sort_keys=True)}`",
            "",
        ]
    )
    lines.extend(
        [
            "## Gate Reasons",
            *[f"- {reason}" for reason in result["verdict_reasons"]],
            "",
            "## Caveat",
            result["transfer_proxy"].get("claim", "Idaho transfer unproven"),
            "",
        ]
    )
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")


def evaluate_maize_baseline(
    *,
    base_csv: str,
    maize_csv: str,
    out_json: str,
    out_md: str,
    n_estimators: int = 400,
    learning_rate: float = 0.05,
) -> dict[str, Any]:
    base = pd.read_csv(base_csv)
    maize = pd.read_csv(maize_csv)
    protocols = {
        "group_kfold": _evaluate_group_kfold(
            base=base,
            maize=maize,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        ),
        "loyo": _evaluate_loyo(
            base=base,
            maize=maize,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
        ),
    }
    no_regression = _base_no_regression(
        base=base,
        maize=maize,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )
    transfer = _transfer_proxy(
        base=base,
        maize=maize,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )
    verdict, reasons = resolve_verdict(
        protocols=protocols,
        base_no_regression=no_regression,
        transfer_proxy=transfer,
    )
    result: dict[str, Any] = {
        "verdict": verdict,
        "verdict_reasons": reasons,
        "protocols": protocols,
        "base_no_regression": no_regression,
        "transfer_proxy": transfer,
        "thresholds": {
            "max_mae": MAX_MAE,
            "max_abs_bias": MAX_ABS_BIAS,
            "valid_vwc_range": [VALID_VWC_MIN, VALID_VWC_MAX],
            "base_no_regression_tolerance_rmse": NO_REGRESSION_TOLERANCE_RMSE,
        },
        "provenance": {
            "git_commit": _git_commit(),
            "base_csv_sha256": _sha256(base_csv),
            "maize_csv_sha256": _sha256(maize_csv),
            "registry_md5s": _registry_md5s(),
            "hyperparams": {
                "n_estimators": n_estimators,
                "learning_rate": learning_rate,
            },
        },
    }
    output = Path(out_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    _write_markdown(out_md, result)
    return result


def main() -> None:
    args = parse_args()
    evaluate_maize_baseline(
        base_csv=args.base_csv,
        maize_csv=args.maize_csv,
        out_json=args.out_json,
        out_md=args.out_md,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
    )


if __name__ == "__main__":
    main()
