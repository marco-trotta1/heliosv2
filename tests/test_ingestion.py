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
