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
