from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from helios.scripts.training_shared import (
    CROP_TYPES,
    DRAINAGE_CLASSES,
    GROWTH_STAGES,
    IRRIGATION_TYPES,
    SOIL_TEXTURES,
)
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
    return df.drop(columns=[col for col in ["field_id", "primary_sensor_id"] if col in df.columns], errors="ignore")


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


def build_expected_feature_columns() -> list[str]:
    categories = {
        "soil_texture": SOIL_TEXTURES,
        "drainage_class": DRAINAGE_CLASSES,
        "irrigation_type": IRRIGATION_TYPES,
        "growth_stage": GROWTH_STAGES,
        "crop_type": CROP_TYPES,
    }
    row_count = max(len(values) for values in categories.values())
    rows = []
    for index in range(row_count):
        rows.append(
            {
                "field_id": f"schema-check-{index}",
                "forecast_horizon_hours": 72,
                "temperature_f": 80.0,
                "humidity_pct": 45.0,
                "wind_mph": 7.0,
                "precipitation_in": 0.0,
                "solar_radiation_mj_m2": 22.0,
                "rolling_temp_mean": 80.0,
                "rolling_humidity_mean": 45.0,
                "rolling_precip_in": 0.0,
                "rolling_solar_mean": 22.0,
                "current_soil_moisture": 0.24,
                "soil_moisture_lag_1": 0.25,
                "soil_moisture_lag_2": 0.26,
                "soil_moisture_delta_1": -0.01,
                "soil_moisture_delta_2": -0.01,
                "moisture_min": 0.22,
                "moisture_max": 0.27,
                "moisture_mean": 0.245,
                "moisture_spread": 0.05,
                "physical_sensor_count": 2,
                "pump_capacity_in_per_hour": 0.25,
                "water_rights_schedule_count": 1,
                "energy_window_count": 1,
                "irrigation_type": categories["irrigation_type"][index % len(categories["irrigation_type"])],
                "soil_texture": categories["soil_texture"][index % len(categories["soil_texture"])],
                "infiltration_rate_in_per_hour": 0.5,
                "slope_pct": 2.0,
                "drainage_class": categories["drainage_class"][index % len(categories["drainage_class"])],
                "crop_type": categories["crop_type"][index % len(categories["crop_type"])],
                "growth_stage": categories["growth_stage"][index % len(categories["growth_stage"])],
                "max_irrigation_volume_in": 1.0,
                "field_area_acres": 100.0,
                "budget_dollars": 600.0,
                "cumulative_irrigation_24h": 0.1,
                "cumulative_irrigation_72h": 0.3,
                "sensor_count": 2,
                "primary_sensor_id": "sensor-a",
                "season_month": 7,
                "openet_monthly_et_in": 0.05,
            }
        )
    return list(build_inference_features(pd.DataFrame(rows)).columns)


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
