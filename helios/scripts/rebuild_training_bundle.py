from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from helios.data.training_schema import validate_training_frame
from helios.models.train_model import train_model
from helios.scripts.download_public_datasets import find_dataset, load_registry
from helios.scripts.generate_sample_data import generate_sample_data
from helios.scripts.parse_mickelson_data import parse_mickelson


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Helios training data and model artifacts.")
    parser.add_argument("--mickelson-workbook", default="data/Water_usage_2024.xlsx")
    parser.add_argument("--openet-csv", default="data/openet_sample.csv")
    parser.add_argument("--synthetic-rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample-output", default="data/sample_training_data.csv")
    parser.add_argument("--mickelson-output", default="data/mickelson_training_data.csv")
    parser.add_argument(
        "--usda-lirf-csv",
        default=None,
        help="Optional USDA LIRF Helios-compatible training CSV from parse_usda_lirf_data.",
    )
    parser.add_argument("--combined-output", default="data/combined_training_data.csv")
    parser.add_argument("--model-path", default="artifacts/moisture_model.pkl")
    parser.add_argument("--metadata-path", default="artifacts/model_metadata.json")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--openet-latitude", type=float, default=None)
    parser.add_argument("--openet-longitude", type=float, default=None)
    parser.add_argument("--openet-coordinate-note", default="")
    return parser.parse_args()


def _maybe_openet_csv(path: str) -> str | None:
    candidate = Path(path)
    return str(candidate) if candidate.exists() else None


def _record_training_provenance(
    *,
    metadata_path: str,
    mickelson_workbook: str,
    openet_csv: str | None,
    usda_lirf_csv: str | None,
    combined: pd.DataFrame,
    openet_latitude: float | None,
    openet_longitude: float | None,
    openet_coordinate_note: str,
) -> None:
    path = Path(metadata_path)
    metadata = json.loads(path.read_text())
    metadata["training_inputs"] = {
        "mickelson_workbook": mickelson_workbook,
        "openet_csv": openet_csv,
        "usda_lirf_csv": usda_lirf_csv,
    }
    source_counts = (
        combined["source_id"].value_counts().sort_index().astype(int).to_dict()
        if "source_id" in combined.columns
        else {}
    )
    provenance: dict[str, object] = {
        "source_counts": source_counts,
        "contains_private_local_derivatives": bool(Path(mickelson_workbook).exists()),
    }
    if usda_lirf_csv is not None:
        maize = combined[combined["source_id"] == "usda_lirf_2012_2013"] if "source_id" in combined.columns else pd.DataFrame()
        if not maize.empty:
            prediction_times = pd.to_datetime(maize["prediction_time"], errors="coerce")
            provenance["maize_years"] = sorted(int(year) for year in prediction_times.dt.year.dropna().unique())
            field_parts = maize["field_id"].astype(str).str.extract(r"_trt_(\d+)$")[0]
            provenance["maize_treatments"] = sorted(int(value) for value in field_parts.dropna().unique())

        normalized_path = Path(usda_lirf_csv).with_name("usda_lirf_normalized_examples.csv")
        measured_count = 0
        interpolated_count = 0
        if normalized_path.exists():
            normalized = pd.read_csv(normalized_path)
            measured_count = int(normalized["target_source"].eq("root_zone_weighted_swc").sum())
            interpolated_count = int(normalized["target_source"].astype(str).str.endswith("_daily_interpolated").sum())
        elif not maize.empty:
            target_source_columns = [
                column for column in ["target_source_24h", "target_source_48h", "target_source_72h"]
                if column in maize.columns
            ]
            for column in target_source_columns:
                measured_count += int(maize[column].eq("root_zone_weighted_swc").sum())
                interpolated_count += int(maize[column].astype(str).str.endswith("_daily_interpolated").sum())
        provenance["maize_label_counts"] = {
            "measured": measured_count,
            "interpolated": interpolated_count,
        }

        try:
            dataset = find_dataset(load_registry(), "usda_lirf_2012_2013")
            provenance["maize_dataset"] = {
                "doi": dataset.get("doi"),
                "license": dataset.get("license"),
            }
        except KeyError:
            provenance["maize_dataset"] = {"doi": None, "license": None}

    metadata["training_provenance"] = provenance
    if openet_latitude is not None and openet_longitude is not None:
        metadata["openet_coordinate"] = {
            "latitude": openet_latitude,
            "longitude": openet_longitude,
            "note": openet_coordinate_note,
        }
    path.write_text(json.dumps(metadata, indent=2))


def rebuild_training_bundle(
    *,
    mickelson_workbook: str,
    openet_csv: str | None,
    synthetic_rows: int,
    seed: int,
    sample_output: str,
    mickelson_output: str,
    usda_lirf_csv: str | None,
    combined_output: str,
    model_path: str,
    metadata_path: str,
    n_estimators: int,
    learning_rate: float,
    openet_latitude: float | None = None,
    openet_longitude: float | None = None,
    openet_coordinate_note: str = "",
) -> dict[str, int | str]:
    openet_path = _maybe_openet_csv(openet_csv) if openet_csv is not None else None

    sample_frame = generate_sample_data(
        rows=synthetic_rows,
        output_path=sample_output,
        seed=seed,
        openet_csv=openet_path,
    )
    mickelson_frame = parse_mickelson(
        input_path=mickelson_workbook,
        output_path=mickelson_output,
        openet_csv=openet_path,
    )

    # Validate each source before concat so a malformed frame names its source instead of
    # surfacing as a confusing combined-frame failure downstream.
    validate_training_frame(sample_frame, source="synthetic")
    validate_training_frame(mickelson_frame, source="mickelson")

    frames = [sample_frame, mickelson_frame]
    usda_lirf_rows = 0
    if usda_lirf_csv is not None:
        usda_lirf_path = Path(usda_lirf_csv)
        if not usda_lirf_path.exists():
            raise FileNotFoundError(f"USDA LIRF CSV not found: {usda_lirf_csv}")
        usda_lirf_frame = pd.read_csv(usda_lirf_path)
        validate_training_frame(usda_lirf_frame, source="usda_lirf")
        usda_lirf_rows = len(usda_lirf_frame)
        frames.append(usda_lirf_frame)

    combined = pd.concat(frames, ignore_index=True)
    if "source_id" not in combined.columns or "field_id" not in combined.columns:
        raise ValueError("Combined training data must include source_id and field_id.")
    if combined[["source_id", "field_id"]].isna().any().any():
        raise ValueError("Combined training data source_id and field_id must be non-null.")
    combined_path = Path(combined_output)
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(combined_path, index=False)

    train_model(
        data_path=str(combined_path),
        model_path=model_path,
        metadata_path=metadata_path,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        group_column="field_id",
    )
    _record_training_provenance(
        metadata_path=metadata_path,
        mickelson_workbook=mickelson_workbook,
        openet_csv=openet_path,
        usda_lirf_csv=usda_lirf_csv,
        combined=combined,
        openet_latitude=openet_latitude,
        openet_longitude=openet_longitude,
        openet_coordinate_note=openet_coordinate_note,
    )

    return {
        "synthetic_rows": len(sample_frame),
        "mickelson_rows": len(mickelson_frame),
        "usda_lirf_rows": usda_lirf_rows,
        "combined_rows": len(combined),
        "combined_output": str(combined_path),
        "model_path": model_path,
        "metadata_path": metadata_path,
    }


def main() -> None:
    args = parse_args()
    result = rebuild_training_bundle(
        mickelson_workbook=args.mickelson_workbook,
        openet_csv=args.openet_csv,
        synthetic_rows=args.synthetic_rows,
        seed=args.seed,
        sample_output=args.sample_output,
        mickelson_output=args.mickelson_output,
        usda_lirf_csv=args.usda_lirf_csv,
        combined_output=args.combined_output,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        openet_latitude=args.openet_latitude,
        openet_longitude=args.openet_longitude,
        openet_coordinate_note=args.openet_coordinate_note,
    )
    logger.info(
        "Rebuilt Helios bundle: synthetic_rows={synthetic_rows} mickelson_rows={mickelson_rows} "
        "usda_lirf_rows={usda_lirf_rows} "
        "combined_rows={combined_rows} model={model_path}".format(**result)
    )


if __name__ == "__main__":
    main()
