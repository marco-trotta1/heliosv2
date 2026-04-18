from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from helios.schemas.outputs import PredictionResponse
from tests.conftest import write_fake_model_artifacts


class DummyRecommendationService:
    def __init__(self, response: PredictionResponse) -> None:
        self.response = response
        self.calls = 0
        self.last_request = None

    def predict_recommendation(self, request) -> PredictionResponse:
        self.calls += 1
        self.last_request = request
        return self.response


def test_health_reports_degraded_when_model_is_unavailable(app_factory) -> None:
    with app_factory(recommendation_service=None, database_ready=True, startup_issues=["Model artifacts are missing."]) as client:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ready"] is False
    assert "Model artifacts are missing." in body["issues"]


def test_predict_success_returns_structured_response(app_factory, prediction_payload, prediction_response) -> None:
    service = DummyRecommendationService(prediction_response)

    with app_factory(recommendation_service=service, database_ready=True) as client:
        response = client.post("/predict", json=prediction_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "water"
    assert body["regional_insights"]["comparable_samples"] == 4
    assert service.calls == 1


def test_predict_returns_503_when_runtime_is_not_ready(app_factory, prediction_payload) -> None:
    with app_factory(recommendation_service=None, database_ready=True, startup_issues=["Model artifacts are missing."]) as client:
        response = client.post("/predict", json=prediction_payload)

    assert response.status_code == 503
    assert response.json()["error_code"] == "service_unavailable"


def test_predict_validation_errors_are_structured(app_factory, prediction_payload, prediction_response) -> None:
    service = DummyRecommendationService(prediction_response)
    payload = dict(prediction_payload)
    payload["forecast_horizon_hours"] = 99

    with app_factory(recommendation_service=service, database_ready=True) as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["issues"]


def test_feedback_submission_prevents_duplicates(app_factory, feedback_payload) -> None:
    with app_factory(recommendation_service=None, database_ready=True) as client:
        first = client.post("/api/feedback", json=feedback_payload)
        second = client.post("/api/feedback", json=feedback_payload)

    assert first.status_code == 201
    assert first.json()["duplicate_prevented"] is False
    assert second.status_code == 201
    assert second.json()["duplicate_prevented"] is True


def test_nearby_feedback_uses_comparability_filters(app_factory, feedback_payload) -> None:
    mismatched = dict(feedback_payload)
    mismatched["farm_id"] = "farm-002"
    mismatched["soil_texture"] = "clay"

    with app_factory(recommendation_service=None, database_ready=True) as client:
        client.post("/api/feedback", json=feedback_payload)
        client.post("/api/feedback", json=mismatched)
        response = client.get(
            "/api/feedback/nearby",
            params={
                "lat": feedback_payload["location_lat"],
                "lon": feedback_payload["location_lon"],
                "radius": 50,
                "crop_type": feedback_payload["crop_type"],
                "recommendation_type": feedback_payload["recommendation_type"],
                "soil_texture": feedback_payload["soil_texture"],
                "irrigation_type": feedback_payload["irrigation_type"],
                "growth_stage": feedback_payload["growth_stage"],
                "season_month": datetime.fromisoformat(feedback_payload["timestamp"]).month,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_samples"] == 1
    assert body["comparable_samples"] == 1


def test_rate_limit_returns_429(temp_settings_env, monkeypatch, prediction_payload, prediction_response) -> None:
    import helios.api.main as main_module
    from helios.api.rate_limit import InMemoryRateLimiter, RateLimitPolicy
    from helios.api.runtime import AppRuntime
    from helios.config import get_settings
    from helios.database.db import init_db

    monkeypatch.setenv("HELIOS_RATE_LIMIT_MAX_REQUESTS", "1")
    get_settings.cache_clear()
    service = DummyRecommendationService(prediction_response)

    def fake_build_runtime(settings):
        init_db()
        return AppRuntime(
            settings=settings,
            recommendation_service=service,
            database_ready=True,
            startup_issues=[],
            rate_limiter=InMemoryRateLimiter(
                RateLimitPolicy(
                    window_seconds=settings.rate_limit_window_seconds,
                    max_requests=settings.rate_limit_max_requests,
                )
            ),
        )

    monkeypatch.setattr(main_module, "build_runtime", fake_build_runtime)
    app = main_module.create_app(get_settings())
    with TestClient(app) as client:
        first = client.post("/predict", json=prediction_payload)
        second = client.post("/predict", json=prediction_payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error_code"] == "rate_limited"


def _build_keyed_app(monkeypatch, main_module, service, api_key: str):
    """Helper: create an app with HELIOS_API_KEY set and a stubbed runtime."""
    from helios.api.runtime import AppRuntime
    from helios.config import get_settings

    monkeypatch.setenv("HELIOS_API_KEY", api_key)
    get_settings.cache_clear()

    monkeypatch.setattr(
        main_module,
        "build_runtime",
        lambda settings: AppRuntime(
            settings=settings,
            recommendation_service=service,
            database_ready=True,
            startup_issues=[],
        ),
    )
    return main_module.create_app(get_settings())


def test_predict_returns_401_when_api_key_set_and_header_missing(
    temp_settings_env, monkeypatch, prediction_payload, prediction_response
) -> None:
    import helios.api.main as main_module

    service = DummyRecommendationService(prediction_response)
    app = _build_keyed_app(monkeypatch, main_module, service, "secret-test-key")
    with TestClient(app) as client:
        response = client.post("/predict", json=prediction_payload)

    assert response.status_code == 401
    assert response.json()["error_code"] == "unauthorized"


def test_predict_returns_200_when_api_key_set_and_header_correct(
    temp_settings_env, monkeypatch, prediction_payload, prediction_response
) -> None:
    import helios.api.main as main_module

    service = DummyRecommendationService(prediction_response)
    app = _build_keyed_app(monkeypatch, main_module, service, "secret-test-key")
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json=prediction_payload,
            headers={"Authorization": "Bearer secret-test-key"},
        )

    assert response.status_code == 200


def test_predict_works_without_header_when_api_key_unset(
    app_factory, prediction_payload, prediction_response
) -> None:
    # HELIOS_API_KEY is not set in temp_settings_env, so auth is disabled
    service = DummyRecommendationService(prediction_response)
    with app_factory(recommendation_service=service, database_ready=True) as client:
        response = client.post("/predict", json=prediction_payload)

    assert response.status_code == 200


def test_predict_uses_caller_supplied_weather_without_noaa(
    app_factory, monkeypatch, prediction_payload, prediction_response
) -> None:
    service = DummyRecommendationService(prediction_response)

    def fail_noaa(*_args, **_kwargs):
        raise AssertionError("NOAA fetch should not run when the caller supplied all weather fields.")

    monkeypatch.setattr("helios.api.routes.fetch_noaa_weather", fail_noaa)

    with app_factory(recommendation_service=service, database_ready=True) as client:
        response = client.post("/predict", json=prediction_payload)

    assert response.status_code == 200
    assert service.last_request.weather.temperature_f == prediction_payload["weather"]["temperature_f"]
    assert service.last_request.weather.solar_radiation_mj_m2 == prediction_payload["weather"]["solar_radiation_mj_m2"]


def test_predict_backfills_missing_weather_from_noaa(
    app_factory, monkeypatch, prediction_payload, prediction_response
) -> None:
    service = DummyRecommendationService(prediction_response)
    payload = dict(prediction_payload)
    payload["weather"] = dict(prediction_payload["weather"])
    payload["weather"]["temperature_f"] = None
    payload["weather"]["solar_radiation_mj_m2"] = None
    del payload["weather"]["wind_mph"]

    noaa_calls: list[tuple[float, float]] = []

    def fake_noaa(lat: float, lon: float) -> dict[str, float | int]:
        noaa_calls.append((lat, lon))
        return {
            "temperature_f": 79.0,
            "humidity_pct": 55.0,
            "wind_mph": 6.5,
            "precipitation_in": 0.1,
            "solar_radiation_mj_m2": 20.0,
            "forecast_horizon_hours": 72,
        }

    monkeypatch.setattr("helios.api.routes.fetch_noaa_weather", fake_noaa)

    with app_factory(recommendation_service=service, database_ready=True) as client:
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert noaa_calls == [(payload["location_lat"], payload["location_lon"])]
    assert service.last_request.weather.temperature_f == 79.0
    assert service.last_request.weather.wind_mph == 6.5
    assert service.last_request.weather.solar_radiation_mj_m2 == 20.0
    assert service.last_request.weather.humidity_pct == prediction_payload["weather"]["humidity_pct"]
    assert service.last_request.weather.precipitation_in == prediction_payload["weather"]["precipitation_in"]


def test_version_returns_hash_and_training_date_without_auth(
    temp_settings_env,
    monkeypatch,
) -> None:
    import helios.api.main as main_module
    from helios.api.runtime import AppRuntime
    from helios.config import get_settings
    from helios.database.db import init_db

    model_path = temp_settings_env["model_path"]
    metadata_path = temp_settings_env["metadata_path"]
    write_fake_model_artifacts(model_path, metadata_path)
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": [],
                "training_date": "2026-04-17T23:00:00+00:00",
            }
        )
    )

    monkeypatch.setenv("HELIOS_API_KEY", "secret-test-key")
    get_settings.cache_clear()

    def fake_build_runtime(settings):
        init_db()
        return AppRuntime(
            settings=settings,
            recommendation_service=None,
            database_ready=True,
            startup_issues=[],
        )

    monkeypatch.setattr(main_module, "build_runtime", fake_build_runtime)
    app = main_module.create_app(get_settings())
    with TestClient(app) as client:
        response = client.get("/version")

    expected_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()[:12]
    assert response.status_code == 200
    assert response.json() == {
        "model_artifact_hash": expected_hash,
        "training_date": "2026-04-17T23:00:00+00:00",
        "api_version": "1.0.0",
    }


def test_version_returns_model_not_loaded_when_artifact_missing(app_factory) -> None:
    with app_factory(recommendation_service=None, database_ready=True) as client:
        response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["model_artifact_hash"] == "model_not_loaded"
