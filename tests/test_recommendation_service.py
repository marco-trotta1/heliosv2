from __future__ import annotations

import json
from pathlib import Path

from helios.schemas.inputs import PredictionRequest
from helios.services.recommendation_service import RecommendationService, VALIDATION_REGIONAL_INSIGHTS


class StubForecastModel:
    def __init__(self) -> None:
        self.metadata = {
            "cv_rmse_mean": 0.1,
            "model_hash": "abc123def456",
            "training_date": "2026-04-17T23:00:00+00:00",
        }
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


def _stub_feedback(monkeypatch) -> None:
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


def test_recommendation_service_applies_feedback_adjustment(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: _stub_insights(),
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
    assert response.et_source == "openet-fallback"
    assert response.recommendation_adjustment is not None
    assert response.recommendation_adjustment.adjustment_factor == 1.08
    assert response.regional_insights is not None


def test_recommendation_service_stress_probability_not_double_counting_precipitation(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    _stub_feedback(monkeypatch)

    dry_payload = dict(prediction_payload)
    dry_payload["weather"] = {**prediction_payload["weather"], "precipitation_in": 0.0}
    rainy_payload = dict(prediction_payload)
    rainy_payload["weather"] = {**prediction_payload["weather"], "precipitation_in": 1.0}

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )

    dry_response = service.predict_recommendation(PredictionRequest(**dry_payload))
    rainy_response = service.predict_recommendation(PredictionRequest(**rainy_payload))

    # Precipitation already feeds the moisture forecast (here held fixed by the stub model),
    # so it must not separately move the stress probability.
    assert dry_response.explanation.stress_probability == rainy_response.explanation.stress_probability


def test_recommendation_service_single_sensor_uses_only_sensor_as_driving_zone(
    single_sensor_prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**single_sensor_prediction_payload)
    _stub_feedback(monkeypatch)

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
    _stub_feedback(monkeypatch)

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    response = service.predict_recommendation(request)

    assert response.explanation.driving_zone == "sensor-a"
    assert response.explanation.zone_moisture_summary == {"sensor-a": 0.2, "sensor-b": 0.38}
    assert response.explanation.high_variability_flag is True
    assert response.explanation.operator_review_required is True
    assert response.validation_evidence is not None
    assert response.validation_evidence.operator_review_required is True


def test_recommendation_service_passes_physical_sensor_count_to_optimizer(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)
    captured_inputs = {}
    _stub_feedback(monkeypatch)

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
    assert captured_inputs["value"].irrigation_type == "pivot"


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
        lambda **_: dict(VALIDATION_REGIONAL_INSIGHTS),
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


def test_recommendation_service_adds_conservative_validation_evidence(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)
    _stub_feedback(monkeypatch)

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
    )
    response = service.predict_recommendation(request)

    assert response.validation_evidence is not None
    assert response.validation_evidence.validation_mode == "disabled"
    assert response.validation_evidence.model_artifact_hash == "abc123def456"
    assert response.validation_evidence.model_training_date == "2026-04-17T23:00:00+00:00"
    assert response.validation_evidence.et_source == "openet-fallback"
    assert response.validation_evidence.feedback_adjustment_status == "Nearby feedback adjustment available"
    assert response.validation_evidence.driving_zone == response.explanation.driving_zone
    assert response.validation_evidence.high_variability_flag is response.explanation.high_variability_flag
    assert response.validation_evidence.evaluation_verdict == "CANDIDATE_FAIL"
    assert response.validation_evidence.evaluation_artifact == "artifacts/maize_baseline_eval.json"
    assert response.validation_evidence.promotion_allowed is False
    assert response.validation_evidence.confidence_caveat == "Heuristic confidence; not a calibrated uncertainty estimate."
    assert "Field-test evidence" in response.validation_evidence.field_test_caveat
    assert "scientifically validated" not in response.validation_evidence.field_test_caveat.lower()


def test_recommendation_service_reads_explicit_evaluation_artifact_path(
    prediction_payload: dict,
    monkeypatch,
    tmp_path: Path,
) -> None:
    request = PredictionRequest(**prediction_payload)
    _stub_feedback(monkeypatch)
    evaluation_path = tmp_path / "configured-eval.json"
    evaluation_path.write_text(json.dumps({"verdict": "CANDIDATE_FAIL"}))

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
        evaluation_artifact_path=evaluation_path,
    )
    response = service.predict_recommendation(request)

    assert response.validation_evidence is not None
    assert response.validation_evidence.evaluation_verdict == "CANDIDATE_FAIL"
    assert response.validation_evidence.evaluation_artifact == str(evaluation_path)
    assert response.validation_evidence.promotion_allowed is False


def test_recommendation_service_evaluation_artifact_is_independent_of_cwd(
    prediction_payload: dict,
    monkeypatch,
    tmp_path: Path,
) -> None:
    request = PredictionRequest(**prediction_payload)
    _stub_feedback(monkeypatch)
    evaluation_path = tmp_path / "artifacts" / "maize_baseline_eval.json"
    evaluation_path.parent.mkdir()
    evaluation_path.write_text(json.dumps({"verdict": "CANDIDATE_FAIL"}))
    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
        evaluation_artifact_path=evaluation_path,
    )
    response = service.predict_recommendation(request)

    assert response.validation_evidence is not None
    assert response.validation_evidence.evaluation_verdict == "CANDIDATE_FAIL"
    assert response.validation_evidence.evaluation_artifact == str(evaluation_path)


def test_recommendation_service_validation_mode_evidence_says_feedback_disabled(
    prediction_payload: dict,
    monkeypatch,
) -> None:
    request = PredictionRequest(**prediction_payload)

    monkeypatch.setattr(
        "helios.services.recommendation_service.get_regional_insights",
        lambda **_: (_ for _ in ()).throw(AssertionError("Nearby feedback should not run.")),
    )
    monkeypatch.setattr(
        "helios.services.recommendation_service.adjust_recommendation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Adjustment should not run.")),
    )

    service = RecommendationService(
        model=StubForecastModel(),
        model_path=Path("unused-model.pkl"),
        metadata_path=Path("unused-metadata.json"),
        validation_mode=True,
    )
    response = service.predict_recommendation(request)

    assert response.validation_evidence is not None
    assert response.validation_evidence.validation_mode == "enabled"
    assert response.validation_evidence.feedback_adjustment_status == (
        "Validation mode: feedback adjustments disabled"
    )
    assert "nearby feedback adjustments were disabled" in response.validation_evidence.preservation_note
