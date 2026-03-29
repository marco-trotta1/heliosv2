from __future__ import annotations

import time
from datetime import datetime, timezone

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from helios.api.auth import verify_api_key
from helios.api.rate_limit import enforce_rate_limit
from helios.database.db import save_prediction_run
from helios.lib.feedback import create_feedback, get_regional_insights
from helios.schemas.inputs import FeedbackCreateRequest, PredictionRequest
from helios.schemas.outputs import FeedbackResponse, HealthResponse, PredictionResponse, RegionalInsights
from helios.services.recommendation_service import RecommendationService


router = APIRouter()
logger = logging.getLogger(__name__)


def _get_recommendation_service(request: Request) -> RecommendationService:
    runtime = request.app.state.runtime
    service = runtime.recommendation_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is unavailable. Train the model artifacts and restart the API.",
        )
    return service


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


@router.post("/predict", response_model=PredictionResponse)
def predict(
    http_request: Request,
    request: PredictionRequest,
    _: None = Depends(enforce_rate_limit),
    __: None = Depends(verify_api_key),
    service: RecommendationService = Depends(_get_recommendation_service),
) -> PredictionResponse:
    t_start = time.monotonic()
    try:
        response = service.predict_recommendation(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed inside the service. Review server logs and retry.",
        ) from None

    latency_ms = round((time.monotonic() - t_start) * 1000, 1)
    request_id = getattr(http_request.state, "request_id", None)
    logger.info(
        "prediction completed",
        extra={
            "request_id": request_id,
            "field_id": request.field_id,
            "farm_id": request.farm_id,
            "decision": response.decision,
            "recommended_amount_mm": response.recommended_amount_mm,
            "confidence_score": response.confidence_score,
            "latency_ms": latency_ms,
        },
    )

    try:
        save_prediction_run(request, response)
    except Exception:
        logger.exception("Failed to persist prediction run — returning result to caller anyway")

    return response


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
    radius: float = Query(50, gt=0, le=500),
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
            radius_km=radius,
        )
        return RegionalInsights(**insights)
    except Exception:
        logger.exception("Failed to aggregate nearby feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nearby feedback lookup failed. Review server logs and retry.",
        ) from None
