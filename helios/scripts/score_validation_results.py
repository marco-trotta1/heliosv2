from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

import pandas as pd


VALID_VWC_MIN = 0.05
VALID_VWC_MAX = 0.55
MAX_MAE = 0.03
MAX_ABS_BIAS = 0.02
ReferenceRule = Literal["auto", "reference_probe", "driest", "mean"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Helios field validation observations.")
    parser.add_argument("--input", required=True, help="Field validation CSV to score.")
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    parser.add_argument(
        "--reference-rule",
        choices=["auto", "reference_probe", "driest", "mean"],
        default="auto",
        help="Fixed observed-VWC reference rule. Auto prefers reference_probe, then driest, then mean.",
    )
    parser.add_argument("--reference-sensor-id", default=None)
    return parser.parse_args()


def cannot_score(input_path: str) -> dict[str, object]:
    return {
        "status": "CANNOT SCORE: missing field validation data",
        "input": input_path,
        "metrics": {},
        "reference_rule": None,
    }


def _normalize_decision(value: object) -> str | None:
    text = str(value).strip().lower()
    if text in {"water", "apply", "irrigate", "yes"}:
        return "water"
    if text in {"wait", "hold", "no", "none"}:
        return "wait"
    return None


def _require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"Validation data missing required columns: {sorted(missing)}")


def _group_columns(frame: pd.DataFrame) -> list[str]:
    if "run_id" in frame.columns:
        return ["run_id", "horizon_hours"]
    if "prediction_id" in frame.columns:
        return ["prediction_id", "horizon_hours"]
    frame["_validation_row_id"] = range(len(frame))
    return ["_validation_row_id", "horizon_hours"]


def _choose_reference_rows(
    frame: pd.DataFrame,
    *,
    reference_rule: ReferenceRule,
    reference_sensor_id: str | None,
) -> tuple[pd.DataFrame, str]:
    grouped_by = _group_columns(frame)
    if reference_rule == "reference_probe" or (
        reference_rule == "auto" and ("reference_probe" in frame.columns or reference_sensor_id)
    ):
        if reference_sensor_id:
            selected = frame[frame.get("sensor_id", pd.Series(dtype=str)).astype(str) == reference_sensor_id].copy()
        else:
            selected = frame[frame["reference_probe"].astype(bool)].copy()
        if selected.empty:
            raise ValueError("Reference probe rule selected but no matching reference probe rows were found.")
        return selected, "reference_probe"

    if reference_rule == "driest" or (reference_rule == "auto" and "sensor_id" in frame.columns):
        idx = frame.groupby(grouped_by)["observed_vwc"].idxmin()
        return frame.loc[idx].copy(), "driest"

    aggregations = {
        "predicted_vwc": "first",
        "observed_vwc": "mean",
    }
    if "helios_decision" in frame.columns:
        aggregations["helios_decision"] = "first"
    if "researcher_judgment" in frame.columns:
        aggregations["researcher_judgment"] = "first"
    selected = frame.groupby(grouped_by, as_index=False).agg(aggregations)
    return selected, "mean"


def score_validation_data(
    input_path: str,
    *,
    reference_rule: ReferenceRule = "auto",
    reference_sensor_id: str | None = None,
) -> dict[str, object]:
    path = Path(input_path)
    if not path.exists():
        return cannot_score(input_path)

    frame = pd.read_csv(path)
    if frame.empty:
        return cannot_score(input_path)

    _require_columns(frame, {"horizon_hours", "predicted_vwc", "observed_vwc"})
    frame = frame.copy()
    frame["horizon_hours"] = pd.to_numeric(frame["horizon_hours"], errors="raise").astype(int)
    frame["predicted_vwc"] = pd.to_numeric(frame["predicted_vwc"], errors="raise")
    frame["observed_vwc"] = pd.to_numeric(frame["observed_vwc"], errors="raise")

    reference_frame, resolved_rule = _choose_reference_rows(
        frame,
        reference_rule=reference_rule,
        reference_sensor_id=reference_sensor_id,
    )
    reference_frame["error"] = reference_frame["predicted_vwc"] - reference_frame["observed_vwc"]
    reference_frame["abs_error"] = reference_frame["error"].abs()

    by_horizon: dict[str, dict[str, float | int]] = {}
    for horizon, horizon_frame in reference_frame.groupby("horizon_hours"):
        by_horizon[str(int(horizon))] = {
            "mae": round(float(horizon_frame["abs_error"].mean()), 6),
            "bias": round(float(horizon_frame["error"].mean()), 6),
            "count": int(len(horizon_frame)),
        }

    out_of_range_count = int(
        ((reference_frame["predicted_vwc"] < VALID_VWC_MIN) | (reference_frame["predicted_vwc"] > VALID_VWC_MAX)).sum()
    )
    has_decision_data = {"helios_decision", "researcher_judgment"}.issubset(reference_frame.columns)
    agreement_rate = None
    if has_decision_data:
        normalized = reference_frame[["helios_decision", "researcher_judgment"]].apply(
            lambda column: column.map(_normalize_decision)
        )
        comparable = normalized.dropna()
        if not comparable.empty:
            agreement_rate = float((comparable["helios_decision"] == comparable["researcher_judgment"]).mean())

    moisture_thresholds_pass = all(
        metric["mae"] <= MAX_MAE + 1e-9 and abs(metric["bias"]) <= MAX_ABS_BIAS + 1e-9
        for metric in by_horizon.values()
    )
    predictions_valid = out_of_range_count == 0
    decisions_scored = agreement_rate is not None
    decisions_reasonable = agreement_rate == 1.0 if decisions_scored else False

    if moisture_thresholds_pass and predictions_valid and decisions_reasonable:
        status = "VALIDATED"
    elif moisture_thresholds_pass and predictions_valid:
        status = "PROMISING BUT NOT VALIDATED"
    else:
        status = "NOT VALIDATED"

    return {
        "status": status,
        "input": input_path,
        "reference_rule": resolved_rule,
        "metrics": {
            "mae_by_horizon": {horizon: metric["mae"] for horizon, metric in by_horizon.items()},
            "bias_by_horizon": {horizon: metric["bias"] for horizon, metric in by_horizon.items()},
            "counts_by_horizon": {horizon: metric["count"] for horizon, metric in by_horizon.items()},
            "out_of_range_predictions": out_of_range_count,
            "water_wait_agreement": agreement_rate,
        },
        "thresholds": {
            "mae_lte_vwc": MAX_MAE,
            "abs_bias_lte_vwc": MAX_ABS_BIAS,
            "valid_vwc_range": [VALID_VWC_MIN, VALID_VWC_MAX],
        },
    }


def main() -> None:
    args = parse_args()
    result = score_validation_data(
        args.input,
        reference_rule=args.reference_rule,
        reference_sensor_id=args.reference_sensor_id,
    )
    serialized = json.dumps(result, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n")
    print(serialized)


if __name__ == "__main__":
    main()
