from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from helios.api.runtime import validate_model_feature_schema
from helios.data.feature_engineering import build_expected_feature_columns, build_training_features
from helios.models.train_model import _build_cross_validation_splits
from helios.scripts.generate_sample_data import generate_sample_data


def test_build_training_features_drops_provenance_columns_and_object_dtypes(tmp_path: Path) -> None:
    training_path = tmp_path / "training.csv"
    frame = generate_sample_data(rows=12, output_path=str(training_path), seed=42)
    frame["source_id"] = "synthetic"
    frame["prediction_time"] = pd.date_range("2026-06-01", periods=len(frame), freq="D").astype(str)
    frame["target_source_24h"] = "synthetic_balance"
    frame["target_source_48h"] = "synthetic_balance"
    frame["target_source_72h"] = "synthetic_balance"

    features, targets = build_training_features(frame)

    assert list(targets.columns) == [
        "target_moisture_24h",
        "target_moisture_48h",
        "target_moisture_72h",
    ]
    assert {
        "source_id",
        "prediction_time",
        "target_source_24h",
        "target_source_48h",
        "target_source_72h",
    }.isdisjoint(features.columns)
    assert not any(pd.api.types.is_object_dtype(dtype) for dtype in features.dtypes)


def test_expected_feature_columns_match_shipped_metadata_schema() -> None:
    metadata_path = Path("artifacts/model_metadata.json")
    metadata = json.loads(metadata_path.read_text())

    assert build_expected_feature_columns() == metadata["feature_columns"]
    validate_model_feature_schema(metadata_path)


def test_generate_sample_data_labels_synthetic_source(tmp_path: Path) -> None:
    training_path = tmp_path / "training.csv"

    frame = generate_sample_data(rows=12, output_path=str(training_path), seed=42)

    assert set(frame["source_id"]) == {"synthetic"}
    assert set(pd.read_csv(training_path)["source_id"]) == {"synthetic"}


def test_group_kfold_splits_do_not_leak_field_ids(tmp_path: Path) -> None:
    training_path = tmp_path / "training.csv"
    frame = generate_sample_data(rows=60, output_path=str(training_path), seed=42)

    splits = _build_cross_validation_splits(row_count=len(frame), groups=frame["field_id"])

    assert len(splits) == 5
    for train_idx, test_idx in splits:
        train_groups = set(frame.iloc[train_idx]["field_id"])
        test_groups = set(frame.iloc[test_idx]["field_id"])
        assert train_groups.isdisjoint(test_groups)
