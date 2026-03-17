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


def test_prediction_request_rejects_mismatched_field_ids(prediction_payload: dict) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = list(payload["soil_moisture_readings"])
    payload["soil_moisture_readings"][0] = dict(payload["soil_moisture_readings"][0])
    payload["soil_moisture_readings"][0]["field_id"] = "other-field"

    with pytest.raises(ValidationError):
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
