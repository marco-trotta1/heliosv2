from __future__ import annotations

from pathlib import Path

from helios.schemas.inputs import PredictionRequest
from helios.services.recommendation_service import RecommendationService


class StubForecastModel:
    def __init__(self) -> None:
        self.metadata = {"cv_rmse_mean": 0.1}
        self.last_features = None

    def predict(self, features) -> dict[str, float]:
        self.last_features = features.copy()
        return {
            "moisture_24h": 0.22,
            "moisture_48h": 0.15,
            "moisture_72h": 0.12,
        }


def _stub_insights() -> dict[str, float | int | None]:
    return {
        "success_rate": 0.81,
        "avg_yield_delta": 6.0,
        "total_samples": 6,
        "weighted_samples": 4.1,
        "comparable_samples": 4,
        "radius_miles": 31.07,
    }


def test_recommendation_service_applies_feedback_adjustment(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: {
            "success_rate": 0.81,
            "avg_yield_delta": 6.0,
            "total_samples": 6,
            "weighted_samples": 4.1,
            "comparable_samples": 4,
            "radius_miles": 31.07,
        },
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        lambda base_recommendation, insights: {
            "adjusted_recommendation_in": round(base_recommendation * 1.08, 2),
            "adjustment_factor": 1.08,
            "reason": "Comparable nearby feedback was consistently positive, so the recommendation was modestly reinforced.",
        },
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    response = service.predict_recommendation(request)

    assert response.decision == "water"
    assert response.recommendation_adjustment is not None
    assert response.recommendation_adjustment.adjustment_factor == 1.08
    assert response.regional_insights is not None


def test_recommendation_service_single_sensor_uses_only_sensor_as_driving_zone(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = [
        {
            "timestamp": reading["timestamp"],
            "field_id": reading["field_id"],
            "sensor_id": "sensor-a",
            "volumetric_water_content": reading["volumetric_water_content"],
        }
        for reading in prediction_payload["soil_moisture_readings"][:3]
    ]
    request = PredictionRequest(**payload)

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: _stub_insights(),
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        lambda base_recommendation, insights: {
            "adjusted_recommendation_in": base_recommendation,
            "adjustment_factor": 1.0,
            "reason": "No adjustment.",
        },
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    response = service.predict_recommendation(request)

    assert response.explanation.driving_zone == "sensor-a"
    assert response.explanation.zone_moisture_summary == {"sensor-a": 0.22}
    assert response.explanation.high_variability_flag is False


def test_recommendation_service_reports_multi_sensor_summary_and_variability(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    payload = dict(prediction_payload)
    payload["soil_moisture_readings"] = [
        {
            "timestamp": reading["timestamp"],
            "field_id": reading["field_id"],
            "sensor_id": reading["sensor_id"],
            "volumetric_water_content": reading["volumetric_water_content"],
        }
        for reading in prediction_payload["soil_moisture_readings"]
    ]
    payload["soil_moisture_readings"][-1]["volumetric_water_content"] = 0.38
    request = PredictionRequest(**payload)

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: _stub_insights(),
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        lambda base_recommendation, insights: {
            "adjusted_recommendation_in": base_recommendation,
            "adjustment_factor": 1.0,
            "reason": "No adjustment.",
        },
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    response = service.predict_recommendation(request)

    assert response.explanation.driving_zone == "sensor-a"
    assert response.explanation.zone_moisture_summary == {"sensor-a": 0.2, "sensor-b": 0.38}
    assert response.explanation.high_variability_flag is True


def test_recommendation_service_passes_physical_sensor_count_to_optimizer(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)
    captured_inputs = {}

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: _stub_insights(),
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        lambda base_recommendation, insights: {
            "adjusted_recommendation_in": base_recommendation,
            "adjustment_factor": 1.0,
            "reason": "No adjustment.",
        },
    )

    def fake_generate_irrigation_plan(inputs):
        captured_inputs["value"] = inputs
        return {
            "decision": "water",
            "recommended_amount_in": 0.45,
            "timing_window": "tonight",
            "confidence_score": 0.74,
            "soil_dry_threshold": 0.18,
            "soil_wet_threshold": 0.35,
        }

    monkeypatch.setattr(
        "helios.services.recommendation_service.generate_irrigation_plan",
        fake_generate_irrigation_plan,
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    service.predict_recommendation(request)

    assert captured_inputs["value"].physical_sensor_count == 2
    assert captured_inputs["value"].sensor_count == 6


def test_recommendation_service_does_not_reload_model_on_each_prediction(
    monkeypatch,
) -> None:
    calls = {"count": 0}
    fake_model = StubForecastModel()

    def fake_load(model_path, metadata_path):
        calls["count"] += 1
        return fake_model

    monkeypatch.setattr("helios.services.recommendation_service.MoistureForecastModel.load", fake_load)

    service = RecommendationService.from_artifacts(
        model_path=Path("artifacts/moisture_model.pkl"),
        metadata_path=Path("artifacts/model_metadata.json"),
    )

    assert calls["count"] == 1
    assert service.model is fake_model


def test_recommendation_service_uses_runtime_openet_value(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)
    model = StubForecastModel()

    monkeypatch.setattr(
        "helios.services.recommendation_service.resolve_monthly_et_in",
        lambda **_: (0.1234, "openet-live"),
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: {
            "success_rate": 0.0,
            "avg_yield_delta": None,
            "total_samples": 0,
            "weighted_samples": 0.0,
            "comparable_samples": 0,
            "radius_miles": 31.07,
        },
    )

    service = RecommendationService(
        model=model,
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    service.predict_recommendation(request)

    assert model.last_features is not None
    assert float(model.last_features.iloc[0]["openet_monthly_et_in"]) == 0.1234


def test_recommendation_service_validation_mode_disables_feedback_adjustment(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)

    def fail_get_regional_insights(**_kwargs):
        raise AssertionError("Nearby feedback should not run in validation mode.")

    def fail_adjust_recommendation(*_args, **_kwargs):
        raise AssertionError("Recommendation adjustment should not run in validation mode.")

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        fail_get_regional_insights,
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        fail_adjust_recommendation,
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
        validation_mode=True,
    )
    response = service.predict_recommendation(request)

    assert response.recommended_amount_in == response.recommendation_adjustment.adjusted_recommendation_in
    assert response.recommendation_adjustment.adjustment_factor == 1.0
    assert response.regional_insights is not None
    assert response.regional_insights.total_samples == 0
    assert "Validation mode is enabled" in response.recommendation_adjustment.reason
