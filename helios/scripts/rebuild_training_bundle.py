from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from helios.models.train_model import train_model
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
    parser.add_argument("--combined-output", default="data/combined_training_data.csv")
    parser.add_argument("--model-path", default="artifacts/moisture_model.pkl")
    parser.add_argument("--metadata-path", default="artifacts/model_metadata.json")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    return parser.parse_args()


def _maybe_openet_csv(path: str) -> str | None:
    candidate = Path(path)
    return str(candidate) if candidate.exists() else None


def rebuild_training_bundle(
    *,
    mickelson_workbook: str,
    openet_csv: str | None,
    synthetic_rows: int,
    seed: int,
    sample_output: str,
    mickelson_output: str,
    combined_output: str,
    model_path: str,
    metadata_path: str,
    n_estimators: int,
    learning_rate: float,
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

    combined = pd.concat([sample_frame, mickelson_frame], ignore_index=True)
    combined_path = Path(combined_output)
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(combined_path, index=False)

    train_model(
        data_path=str(combined_path),
        model_path=model_path,
        metadata_path=metadata_path,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )

    return {
        "synthetic_rows": len(sample_frame),
        "mickelson_rows": len(mickelson_frame),
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
        combined_output=args.combined_output,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
    )
    logger.info(
        "Rebuilt Helios bundle: synthetic_rows={synthetic_rows} mickelson_rows={mickelson_rows} "
        "combined_rows={combined_rows} model={model_path}".format(**result)
    )


if __name__ == "__main__":
    main()
