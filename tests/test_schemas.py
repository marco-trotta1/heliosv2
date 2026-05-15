from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from helios.schemas.inputs import FeedbackCreateRequest, PredictionRequest


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
