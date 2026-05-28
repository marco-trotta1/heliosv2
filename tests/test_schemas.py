from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from helios.schemas.inputs import FeedbackCreateRequest, PredictionRequest, PredictionRequestPayload


def test_prediction_request_defaults_farm_id(prediction_payload: dict) -> None:
    payload = dict(prediction_payload)
    payload["farm_id"] = None

    request = PredictionRequest(**payload)

    assert request.farm_id == request.field_id


def test_prediction_request_allows_single_sensor_with_three_readings(single_sensor_prediction_payload: dict) -> None:
    request = PredictionRequest(**single_sensor_prediction_payload)

    assert len({reading.sensor_id for reading in request.soil_moisture_readings}) == 1


def test_prediction_request_allows_multi_sensor_readings(prediction_payload: dict) -> None:
    request = PredictionRequest(**prediction_payload)

    assert len({reading.sensor_id for reading in request.soil_moisture_readings}) == 2


def test_prediction_request_rejects_mismatched_field_ids(prediction_payload: dict) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = list(payload["soil_moisture_readings"])
    payload["soil_moisture_readings"][0] = dict(payload["soil_moisture_readings"][0])
    payload["soil_moisture_readings"][0]["field_id"] = "other-field"

    with pytest.raises(ValidationError):
        PredictionRequest(**payload)


def test_prediction_request_rejects_sensor_with_too_few_readings(prediction_payload: dict) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = list(prediction_payload["soil_moisture_readings"][:5])

    with pytest.raises(ValidationError, match="sensor 'sensor-b' requires at least 3 soil moisture readings; received 2"):
        PredictionRequest(**payload)


def test_prediction_request_requires_sensor_id(prediction_payload: dict) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = list(payload["soil_moisture_readings"])
    payload["soil_moisture_readings"][0] = dict(payload["soil_moisture_readings"][0])
    del payload["soil_moisture_readings"][0]["sensor_id"]

    with pytest.raises(ValidationError, match="sensor_id"):
        PredictionRequest(**payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("temperature_f", 140.0),
        ("wind_mph", 90.0),
        ("precipitation_in", 13.0),
        ("solar_radiation_mj_m2", 36.0),
    ],
)
def test_prediction_request_rejects_implausible_weather(
    prediction_payload: dict,
    field_name: str,
    invalid_value: float,
) -> None:
    payload = deepcopy(prediction_payload)
    payload["weather"][field_name] = invalid_value

    with pytest.raises(ValidationError):
        PredictionRequest(**payload)


def test_prediction_payload_rejects_implausible_weather_patch(prediction_payload: dict) -> None:
    payload = deepcopy(prediction_payload)
    payload["weather"] = {
        "wind_mph": 90.0,
    }

    with pytest.raises(ValidationError):
        PredictionRequestPayload(**payload)


def test_prediction_request_rejects_unsupported_crop_type(prediction_payload: dict) -> None:
    payload = deepcopy(prediction_payload)
    payload["crop"]["crop_type"] = "wheat"

    with pytest.raises(ValidationError):
        PredictionRequest(**payload)


def test_prediction_timestamps_are_normalized_to_utc(prediction_payload: dict) -> None:
    payload = deepcopy(prediction_payload)
    payload["soil_moisture_readings"][0]["timestamp"] = "2026-03-17T06:00:00-06:00"
    payload["recent_irrigation_events"][0]["timestamp"] = "2026-03-16T12:00:00-06:00"

    request = PredictionRequest(**payload)

    assert request.soil_moisture_readings[0].timestamp == datetime(
        2026,
        3,
        17,
        12,
        0,
        tzinfo=timezone.utc,
    )
    assert request.recent_irrigation_events[0].timestamp == datetime(
        2026,
        3,
        16,
        18,
        0,
        tzinfo=timezone.utc,
    )


@pytest.mark.parametrize(
    ("collection_name", "timestamp"),
    [
        ("soil_moisture_readings", "2026-03-17T00:00:00"),
        ("recent_irrigation_events", "2026-03-17T00:00:00"),
    ],
)
def test_prediction_request_rejects_naive_timestamps(
    prediction_payload: dict,
    collection_name: str,
    timestamp: str,
) -> None:
    payload = deepcopy(prediction_payload)
    payload[collection_name][0]["timestamp"] = timestamp

    with pytest.raises(ValidationError, match="timezone-aware"):
        PredictionRequest(**payload)


@pytest.mark.parametrize(
    "collection_name",
    ["soil_moisture_readings", "recent_irrigation_events"],
)
def test_prediction_request_rejects_future_timestamps(
    prediction_payload: dict,
    collection_name: str,
) -> None:
    payload = deepcopy(prediction_payload)
    payload[collection_name][0]["timestamp"] = (
        datetime.now(timezone.utc) + timedelta(minutes=10)
    ).isoformat()

    with pytest.raises(ValidationError, match="future"):
        PredictionRequest(**payload)


def test_feedback_request_rejects_future_timestamp(feedback_payload: dict) -> None:
    payload = dict(feedback_payload)
    payload["timestamp"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    with pytest.raises(ValidationError):
        FeedbackCreateRequest(**payload)


def test_feedback_request_normalizes_blank_notes(feedback_payload: dict) -> None:
    payload = dict(feedback_payload)
    payload["notes"] = "   "

    request = FeedbackCreateRequest(**payload)

    assert request.notes is None
