"""The training-row contract — one explicit home for the wide-CSV schema.

Three parsers (synthetic, Mickelson, USDA LIRF) emit training rows that the trainer
concatenates and consumes. Before this module the contract was implicit and scattered
(SCHEMA_COLUMNS in mickelson_support, TRAINING_COLUMNS in parse_usda_lirf_data,
TARGET_COLUMNS / CATEGORICAL_COLUMNS / a hardcoded drop-list in feature_engineering, and a
one-column check in train_model). They now all derive from the column groups here, and
``validate_training_frame`` is the seam where a malformed frame fails loudly — naming the
source — instead of silently injecting NaNs or breaking XGBoost downstream.

Adding a new column (e.g. the corn-baseline ``source_id`` group key or per-horizon
``target_source``) means registering it here once: add it to NON_FEATURE_COLUMNS (metadata,
dropped before features) or the appropriate group. The validator rejects unregistered
columns, so registration can't be forgotten.
"""

from __future__ import annotations

import pandas as pd

from helios.scripts.training_shared import (
    CROP_TYPES,
    DRAINAGE_CLASSES,
    GROWTH_STAGES,
    IRRIGATION_TYPES,
    SOIL_TEXTURES,
)


class TrainingSchemaError(ValueError):
    """Raised when a training frame violates the training-row contract."""


# Canonical wide-CSV columns, in order. The synthetic and USDA parsers emit all of these;
# Mickelson emits everything except the OPTIONAL_COLUMNS below.
CANONICAL_COLUMNS = [
    "field_id",
    "forecast_horizon_hours",
    "temperature_f",
    "humidity_pct",
    "wind_mph",
    "precipitation_in",
    "solar_radiation_mj_m2",
    "rolling_temp_mean",
    "rolling_humidity_mean",
    "rolling_precip_in",
    "rolling_solar_mean",
    "current_soil_moisture",
    "soil_moisture_lag_1",
    "soil_moisture_lag_2",
    "soil_moisture_delta_1",
    "soil_moisture_delta_2",
    "moisture_min",
    "moisture_max",
    "moisture_mean",
    "moisture_spread",
    "physical_sensor_count",
    "pump_capacity_in_per_hour",
    "water_rights_schedule_count",
    "energy_window_count",
    "irrigation_type",
    "soil_texture",
    "infiltration_rate_in_per_hour",
    "slope_pct",
    "drainage_class",
    "crop_type",
    "growth_stage",
    "max_irrigation_volume_in",
    "field_area_acres",
    "budget_dollars",
    "cumulative_irrigation_24h",
    "cumulative_irrigation_72h",
    "sensor_count",
    "season_month",
    "openet_monthly_et_in",
    "reference_et_in",
    "target_moisture_24h",
    "target_moisture_48h",
    "target_moisture_72h",
]

# Source-dependent columns. The Mickelson parser does not derive per-zone sensor spread, so
# its rows omit these and the combined frame carries NaN for them — XGBoost tolerates that.
# Marked OPTIONAL so the validator accepts today's data without forcing a retrain. Closing
# this gap (making Mickelson emit them) is a separate, retraining decision.
OPTIONAL_COLUMNS = [
    "moisture_min",
    "moisture_max",
    "moisture_mean",
    "moisture_spread",
    "physical_sensor_count",
]

# Targets the model predicts.
TARGET_COLUMNS = [
    "target_moisture_24h",
    "target_moisture_48h",
    "target_moisture_72h",
]

# String columns one-hot encoded before training.
CATEGORICAL_COLUMNS = [
    "soil_texture",
    "drainage_class",
    "irrigation_type",
    "growth_stage",
    "crop_type",
]

# Identifier columns dropped before the feature matrix (kept for grouping/debugging).
# primary_sensor_id appears only on the inference path, not in training CSVs. A future
# group key (corn-baseline source_id) belongs here.
NON_FEATURE_COLUMNS = [
    "field_id",
    "primary_sensor_id",
]

# Columns every source must emit and the validator requires present (order preserved, so
# this is exactly the historical mickelson_support.SCHEMA_COLUMNS).
REQUIRED_COLUMNS = [c for c in CANONICAL_COLUMNS if c not in set(OPTIONAL_COLUMNS)]

# Known columns the validator tolerates beyond CANONICAL (inference-only identifiers).
_KNOWN_EXTRA_COLUMNS = {"primary_sensor_id"}

_CATEGORY_VOCAB = {
    "soil_texture": set(SOIL_TEXTURES),
    "drainage_class": set(DRAINAGE_CLASSES),
    "irrigation_type": set(IRRIGATION_TYPES),
    "growth_stage": set(GROWTH_STAGES),
    "crop_type": set(CROP_TYPES),
}

# Volumetric water content is a fraction; targets outside this band signal a unit error
# (e.g. millimetres leaking in) rather than legitimate data.
TARGET_MIN = 0.0
TARGET_MAX = 1.0


def validate_training_frame(df: pd.DataFrame, *, source: str = "training data") -> None:
    """Validate a wide training frame against the contract. Raises TrainingSchemaError.

    Strict by design — training must fail loudly. The inference path keeps its lenient
    warn-and-fill behaviour (helios.data.feature_engineering.prepare_feature_matrix).
    """
    if df.empty:
        raise TrainingSchemaError(f"{source}: training frame is empty")

    columns = set(df.columns)

    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise TrainingSchemaError(f"{source}: missing required columns {missing}")

    allowed = set(CANONICAL_COLUMNS) | _KNOWN_EXTRA_COLUMNS
    unknown = sorted(columns - allowed)
    if unknown:
        raise TrainingSchemaError(
            f"{source}: unregistered columns {unknown} — add them to "
            f"helios/data/training_schema.py (NON_FEATURE_COLUMNS for identifiers, or the "
            f"appropriate feature/target group) so they are handled deliberately"
        )

    for column in TARGET_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().all():
            raise TrainingSchemaError(f"{source}: target column {column!r} is entirely non-numeric/missing")
        present = values.dropna()
        out_of_range = present[(present < TARGET_MIN) | (present > TARGET_MAX)]
        if not out_of_range.empty:
            raise TrainingSchemaError(
                f"{source}: target {column!r} has {len(out_of_range)} value(s) outside "
                f"[{TARGET_MIN}, {TARGET_MAX}] (e.g. {out_of_range.iloc[0]}) — likely a unit error"
            )

    for column, vocab in _CATEGORY_VOCAB.items():
        if column not in columns:
            continue
        seen = set(df[column].dropna().astype(str).unique())
        unexpected = sorted(seen - vocab)
        if unexpected:
            raise TrainingSchemaError(
                f"{source}: categorical {column!r} has values outside the fixed vocabulary "
                f"{unexpected} — they would create phantom one-hot columns"
            )

    _validate_openet(df, source=source)


def _validate_openet(df: pd.DataFrame, *, source: str) -> None:
    if "openet_monthly_et_in" not in df.columns:
        raise TrainingSchemaError(f"{source}: must include openet_monthly_et_in for inference parity")
    values = pd.to_numeric(df["openet_monthly_et_in"], errors="coerce")
    if values.isna().any():
        raise TrainingSchemaError(f"{source}: openet_monthly_et_in contains non-numeric or missing values")
    if (values < 0).any():
        raise TrainingSchemaError(f"{source}: openet_monthly_et_in cannot contain negative values")
    if (values == 0).all():
        raise TrainingSchemaError(f"{source}: openet_monthly_et_in cannot be all zero")
