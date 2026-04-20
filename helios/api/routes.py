from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from helios.api.auth import verify_api_key
from helios.api.rate_limit import enforce_rate_limit
from helios.database.db import save_acknowledgement, save_prediction_run
from helios.lib.feedback import create_feedback, get_regional_insights
from helios.schemas.inputs import AcknowledgementRequest, FeedbackCreateRequest, PredictionRequest, PredictionRequestPayload
from helios.schemas.outputs import FeedbackResponse, HealthResponse, PredictionResponse, RegionalInsights
from helios.services.recommendation_service import RecommendationService
from helios.utils.weather_api import fetch_noaa_weather


router = APIRouter()
logger = logging.getLogger(__name__)
API_VERSION = "1.0.0"
WEATHER_FIELD_NAMES = (
    "temperature_f",
    "humidity_pct",
    "wind_mph",
    "precipitation_in",
    "solar_radiation_mj_m2",
)


def _get_recommendation_service(request: Request) -> RecommendationService:
    runtime = request.app.state.runtime
    service = runtime.recommendation_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is unavailable. Train the model artifacts and restart the API.",
        )
    return service


def _request_log_message(request_id: str, message: str) -> str:
    return f"[req:{request_id}] {message}"


def _model_artifact_hash(model_path: Path) -> str:
    if not model_path.exists():
        return "model_not_loaded"
    return hashlib.sha256(model_path.read_bytes()).hexdigest()[:12]


def _read_training_date(metadata_path: Path) -> str | None:
    if not metadata_path.exists():
        return None

    try:
        metadata = json.loads(metadata_path.read_text())
    except Exception:
        logger.exception(
            "Failed to read model metadata for version endpoint",
            extra={"metadata_path": str(metadata_path)},
        )
        return None

    return metadata.get("training_date") or metadata.get("trained_at")


def _build_prediction_request(payload: PredictionRequestPayload, request_id: str | None) -> PredictionRequest:
    raw_weather = payload.weather.model_dump(exclude_none=False) if payload.weather is not None else {}
    weather_horizon = raw_weather.get("forecast_horizon_hours") or payload.forecast_horizon_hours
    caller_supplied_weather = all(raw_weather.get(field_name) is not None for field_name in WEATHER_FIELD_NAMES)

    if caller_supplied_weather:
        logger.info(
            _request_log_message(request_id, "prediction weather source selected") if request_id else "prediction weather source selected",
            extra={
                "request_id": request_id,
                "field_id": payload.field_id,
                "weather_source": "caller-supplied",
            },
        )
        merged_weather = {
            field_name: raw_weather[field_name]
            for field_name in WEATHER_FIELD_NAMES
        }
    else:
        fetched_weather = fetch_noaa_weather(payload.location_lat, payload.location_lon)
        merged_weather = {
            **fetched_weather,
            **{field_name: raw_weather[field_name] for field_name in WEATHER_FIELD_NAMES if raw_weather.get(field_name) is not None},
        }
        logger.info(
            _request_log_message(request_id, "prediction weather source selected") if request_id else "prediction weather source selected",
            extra={
                "request_id": request_id,
                "field_id": payload.field_id,
                "weather_source": "noaa-fetched",
            },
        )

    try:
        return PredictionRequest(
            **payload.model_dump(exclude={"weather"}),
            weather={
                **merged_weather,
                "forecast_horizon_hours": weather_horizon,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Request validation failed after weather enrichment: {exc}",
        ) from exc


@router.get("/livez")
def livez() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> JSONResponse:
    runtime = request.app.state.runtime
    response = HealthResponse(
        status="ready" if runtime.ready else "degraded",
        ready=runtime.ready,
        model_loaded=runtime.recommendation_service is not None,
        database_ready=runtime.database_ready,
        rate_limit_enabled=True,
        timestamp=datetime.now(timezone.utc),
        issues=runtime.startup_issues,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if runtime.ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(mode="json"),
    )


@router.get("/version")
def version(request: Request) -> dict[str, str | None]:
    runtime = request.app.state.runtime
    model_path = runtime.settings.model_path
    metadata_path = runtime.settings.metadata_path
    return {
        "model_artifact_hash": _model_artifact_hash(model_path),
        "training_date": _read_training_date(metadata_path),
        "api_version": API_VERSION,
        "validation_mode": "enabled" if runtime.settings.validation_mode else "disabled",
    }


@router.post("/predict", response_model=PredictionResponse)
def predict(
    http_request: Request,
    request: PredictionRequestPayload,
    _: None = Depends(enforce_rate_limit),
    __: None = Depends(verify_api_key),
    service: RecommendationService = Depends(_get_recommendation_service),
) -> PredictionResponse:
    t_start = time.monotonic()
    request_id = str(uuid.uuid4())
    http_request.state.request_id = request_id
    try:
        hydrated_request = _build_prediction_request(request, request_id)
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.exception(_request_log_message(request_id, "NOAA weather enrichment failed"))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        response = service.predict_recommendation(hydrated_request)
    except HTTPException:
        raise
    except Exception:
        logger.exception(_request_log_message(request_id, "Prediction failed"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed inside the service. Review server logs and retry.",
        ) from None

    latency_ms = round((time.monotonic() - t_start) * 1000, 1)
    logger.info(
        _request_log_message(request_id, "prediction completed"),
        extra={
            "request_id": request_id,
            "field_id": hydrated_request.field_id,
            "farm_id": hydrated_request.farm_id,
            "decision": response.decision,
            "recommended_amount_in": response.recommended_amount_in,
            "confidence_score": response.confidence_score,
            "latency_ms": latency_ms,
        },
    )

    try:
        save_prediction_run(hydrated_request, response)
    except Exception:
        logger.exception(_request_log_message(request_id, "Failed to persist prediction run — returning result to caller anyway"))

    return response


@router.post("/api/acknowledgements", status_code=status.HTTP_200_OK)
def log_acknowledgement(
    request: AcknowledgementRequest,
    _: None = Depends(enforce_rate_limit),
) -> dict:
    try:
        save_acknowledgement(
            field_id=request.field_id,
            farm_id=request.farm_id,
            timestamp=request.timestamp,
            recommendation_summary=request.recommendation_summary,
        )
    except Exception:
        logger.exception("Failed to persist acknowledgement — not blocking caller")
    return {"status": "ok"}


@router.post("/api/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    request: FeedbackCreateRequest,
    _: None = Depends(enforce_rate_limit),
    __: None = Depends(verify_api_key),
) -> FeedbackResponse:
    try:
        feedback_id, duplicate_prevented = create_feedback(request)
    except Exception:
        logger.exception("Failed to store farmer feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback submission failed. Review server logs and retry.",
        ) from None

    if duplicate_prevented:
        return FeedbackResponse(
            id=feedback_id,
            duplicate_prevented=True,
            message="Duplicate feedback prevented within the protected submission window.",
        )
    return FeedbackResponse(id=feedback_id, message="Feedback recorded.")


@router.get("/api/feedback/nearby", response_model=RegionalInsights)
def nearby_feedback(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: float = Query(31.07, gt=0, le=310.7),
    crop_type: str | None = Query(default=None),
    recommendation_type: str | None = Query(default=None),
    soil_texture: str | None = Query(default=None),
    irrigation_type: str | None = Query(default=None),
    growth_stage: str | None = Query(default=None),
    season_month: int | None = Query(default=None, ge=1, le=12),
    _: None = Depends(enforce_rate_limit),
) -> RegionalInsights:
    try:
        insights = get_regional_insights(
            lat=lat,
            lon=lon,
            crop_type=crop_type or "",
            recommendation_type=recommendation_type or "",
            soil_texture=soil_texture or "",
            irrigation_type=irrigation_type or "",
            growth_stage=growth_stage or "",
            season_month=season_month or datetime.now(timezone.utc).month,
            radius_miles=radius,
        )
        return RegionalInsights(**insights)
    except Exception:
        logger.exception("Failed to aggregate nearby feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nearby feedback lookup failed. Review server logs and retry.",
        ) from None
