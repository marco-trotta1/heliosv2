"""Tests for the training-row contract (helios.data.training_schema).

Covers: real parser output passes (calibration), the required-column order is frozen
(no-retrain guard), optional columns are tolerated, and every violation fails loudly.
"""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import pytest

from helios.data import training_schema as schema
from helios.data.training_schema import TrainingSchemaError, validate_training_frame
from helios.scripts.generate_sample_data import generate_sample_data

# Frozen historical column order (== the pre-refactor mickelson_support.SCHEMA_COLUMNS).
# If this changes, the wide-CSV schema changed and the model would need a retrain.
HISTORICAL_REQUIRED_COLUMNS = [
    "field_id", "forecast_horizon_hours", "temperature_f", "humidity_pct", "wind_mph",
    "precipitation_in", "solar_radiation_mj_m2", "rolling_temp_mean", "rolling_humidity_mean",
    "rolling_precip_in", "rolling_solar_mean", "current_soil_moisture", "soil_moisture_lag_1",
    "soil_moisture_lag_2", "soil_moisture_delta_1", "soil_moisture_delta_2",
    "pump_capacity_in_per_hour", "water_rights_schedule_count", "energy_window_count",
    "irrigation_type", "soil_texture", "infiltration_rate_in_per_hour", "slope_pct",
    "drainage_class", "crop_type", "growth_stage", "max_irrigation_volume_in",
    "field_area_acres", "budget_dollars", "cumulative_irrigation_24h", "cumulative_irrigation_72h",
    "sensor_count", "season_month", "openet_monthly_et_in", "reference_et_in",
    "target_moisture_24h", "target_moisture_48h", "target_moisture_72h",
]


@pytest.fixture
def synthetic_frame():
    tmp = os.path.join(tempfile.gettempdir(), "schema_test_sample.csv")
    return generate_sample_data(rows=24, output_path=tmp, seed=7)


def test_required_column_order_frozen():
    # No-retrain guard: the canonical/required column contract must not silently change.
    assert schema.REQUIRED_COLUMNS == HISTORICAL_REQUIRED_COLUMNS
    assert len(schema.CANONICAL_COLUMNS) == 43
    assert len(schema.OPTIONAL_COLUMNS) == 5
    assert set(schema.CANONICAL_COLUMNS) - set(schema.OPTIONAL_COLUMNS) == set(schema.REQUIRED_COLUMNS)


def test_synthetic_output_satisfies_contract(synthetic_frame):
    # Calibration: a real producer's output must validate cleanly.
    validate_training_frame(synthetic_frame, source="synthetic")


def test_mickelson_shaped_frame_without_optional_columns_passes(synthetic_frame):
    # Mickelson omits the optional sensor-spread columns entirely — that must be accepted.
    mickelson_like = synthetic_frame.drop(columns=schema.OPTIONAL_COLUMNS)
    validate_training_frame(mickelson_like, source="mickelson")


def test_optional_columns_may_be_nan(synthetic_frame):
    frame = synthetic_frame.assign(**{col: float("nan") for col in schema.OPTIONAL_COLUMNS})
    validate_training_frame(frame, source="combined")


def test_empty_frame_rejected():
    with pytest.raises(TrainingSchemaError, match="empty"):
        validate_training_frame(pd.DataFrame(columns=schema.CANONICAL_COLUMNS), source="x")


def test_missing_required_column_rejected(synthetic_frame):
    frame = synthetic_frame.drop(columns=["reference_et_in"])
    with pytest.raises(TrainingSchemaError, match="reference_et_in"):
        validate_training_frame(frame, source="x")


def test_unregistered_column_rejected(synthetic_frame):
    # The schema guard: a new column must be registered before training accepts it.
    frame = synthetic_frame.copy()
    frame["unregistered_source_group"] = "usda_lirf_2012_2013"
    with pytest.raises(TrainingSchemaError, match="unregistered_source_group"):
        validate_training_frame(frame, source="x")


def test_target_out_of_range_rejected(synthetic_frame):
    frame = synthetic_frame.copy()
    frame.loc[0, "target_moisture_48h"] = 18.0  # millimetres leaked in
    with pytest.raises(TrainingSchemaError, match="unit error"):
        validate_training_frame(frame, source="x")


def test_unknown_categorical_value_rejected(synthetic_frame):
    frame = synthetic_frame.copy()
    frame.loc[0, "soil_texture"] = "silt"  # not in the fixed vocabulary
    with pytest.raises(TrainingSchemaError, match="vocabulary"):
        validate_training_frame(frame, source="x")


def test_all_zero_openet_rejected(synthetic_frame):
    frame = synthetic_frame.copy()
    frame["openet_monthly_et_in"] = 0.0
    with pytest.raises(TrainingSchemaError, match="all zero"):
        validate_training_frame(frame, source="x")


def test_negative_openet_rejected(synthetic_frame):
    frame = synthetic_frame.copy()
    frame.loc[0, "openet_monthly_et_in"] = -0.1
    with pytest.raises(TrainingSchemaError, match="negative"):
        validate_training_frame(frame, source="x")


def test_source_name_in_error(synthetic_frame):
    frame = synthetic_frame.drop(columns=["reference_et_in"])
    with pytest.raises(TrainingSchemaError, match="usda_lirf"):
        validate_training_frame(frame, source="usda_lirf")
