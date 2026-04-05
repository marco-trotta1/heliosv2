from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from helios.utils.evapotranspiration import estimate_reference_et_in

logger = logging.getLogger(__name__)


TARGET_COLUMNS = [
    "target_moisture_24h",
    "target_moisture_48h",
    "target_moisture_72h",
]

CATEGORICAL_COLUMNS = [
    "soil_texture",
    "drainage_class",
    "irrigation_type",
    "growth_stage",
    "crop_type",
]


def _one_hot_encode(df: pd.DataFrame) -> pd.DataFrame:
    encoded = pd.get_dummies(df, columns=[col for col in CATEGORICAL_COLUMNS if col in df.columns], dtype=float)
    return encoded


def _ensure_reference_et(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    if "reference_et_in" not in enriched.columns:
        enriched["reference_et_in"] = enriched.apply(
            lambda row: estimate_reference_et_in(
                temperature_f=float(row["rolling_temp_mean"]),
                humidity_pct=float(row["rolling_humidity_mean"]),
                wind_mph=float(row["wind_mph"]),
                solar_radiation_mj_m2=float(row["rolling_solar_mean"]),
            ),
            axis=1,
        )
    return enriched


def _drop_non_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[col for col in ["field_id"] if col in df.columns], errors="ignore")


def build_training_features(
    df: pd.DataFrame,
    openet_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = _drop_non_feature_columns(df.copy())

    if openet_df is not None and not openet_df.empty:
        working = working.merge(openet_df[["date", "openet_et_mm"]], on="date", how="left")
        working["et_source"] = working["openet_et_mm"].apply(
            lambda v: "openet" if pd.notna(v) else "fao56"
        )

    working = _ensure_reference_et(working)
    targets = working[TARGET_COLUMNS].copy()
    features = working.drop(columns=TARGET_COLUMNS, errors="ignore")
    features = _one_hot_encode(features)
    return features, targets


def build_inference_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    working = _drop_non_feature_columns(raw_df.copy())
    working = _ensure_reference_et(working)
    return _one_hot_encode(working)


def prepare_feature_matrix(df: pd.DataFrame, feature_columns: Iterable[str] | None = None) -> pd.DataFrame:
    matrix = df.copy()
    if feature_columns is None:
        return matrix

    training_set = set(feature_columns)
    inference_set = set(matrix.columns)

    unseen = inference_set - training_set
    if unseen:
        logger.warning(
            "Inference features contain columns not seen during training — these will be ignored. "
            "This may indicate a new crop type or schema change.",
            extra={"unseen_columns": sorted(unseen)},
        )

    missing = training_set - inference_set
    if missing:
        logger.warning(
            "Training columns are missing from inference features — filling with 0.0. "
            "Predictions may be degraded for affected inputs.",
            extra={"missing_columns": sorted(missing)},
        )

    ordered = pd.DataFrame(index=matrix.index)
    for column in feature_columns:
        ordered[column] = matrix[column] if column in matrix.columns else 0.0
    return ordered.fillna(0.0)
