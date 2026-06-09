from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from helios.data.ingestion import request_to_feature_frame
from helios.schemas.inputs import PredictionRequest


def test_irrigation_sums_exclude_events_after_latest_soil_reading(
    prediction_payload: dict,
) -> None:
    payload = deepcopy(prediction_payload)
    latest_reading = datetime(2026, 3, 17, 18, 0, tzinfo=timezone.utc)
    payload["recent_irrigation_events"] = [
        {
            "timestamp": (latest_reading - timedelta(hours=1)).isoformat(),
            "applied_in": 0.2,
        },
        {
            "timestamp": (latest_reading + timedelta(hours=1)).isoformat(),
            "applied_in": 9.0,
        },
        {
            "timestamp": (latest_reading - timedelta(hours=25)).isoformat(),
            "applied_in": 0.3,
        },
    ]

    frame = request_to_feature_frame(PredictionRequest(**payload))

    assert frame.iloc[0]["cumulative_irrigation_24h"] == pytest.approx(0.2)
    assert frame.iloc[0]["cumulative_irrigation_72h"] == pytest.approx(0.5)


def test_primary_sensor_selection_rejects_stuck_low_outlier(
    prediction_payload: dict,
) -> None:
    payload = deepcopy(prediction_payload)
    latest = datetime(2026, 3, 17, 18, 0, tzinfo=timezone.utc)
    # Three healthy sensors clustered near 0.27 plus one probe stuck near zero.
    readings = []
    sensors = {"sensor-a": 0.27, "sensor-b": 0.28, "sensor-c": 0.26, "stuck": 0.01}
    for sensor_id, vwc in sensors.items():
        for offset in (6, 3, 0):
            readings.append(
                {
                    "timestamp": (latest - timedelta(hours=offset)).isoformat(),
                    "field_id": payload["field_id"],
                    "sensor_id": sensor_id,
                    "volumetric_water_content": vwc,
                }
            )
    payload["soil_moisture_readings"] = readings

    frame = request_to_feature_frame(PredictionRequest(**payload))

    # The stuck probe is discarded, so it neither becomes the driving zone nor drags the
    # current-moisture feature down to ~0.01.
    assert frame.iloc[0]["primary_sensor_id"] != "stuck"
    assert frame.iloc[0]["current_soil_moisture"] >= 0.25
