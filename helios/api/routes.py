from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import logging

from fastapi import APIRouter, HTTPException, Query, status

from helios.database.db import get_engine
from helios.lib.feedback import create_feedback, get_regional_insights
from helios.schemas.inputs import FeedbackCreateRequest, PredictionRequest
from helios.schemas.outputs import FeedbackResponse, HealthResponse, PredictionResponse, RegionalInsights
from helios.services.recommendation_service import RecommendationService


router = APIRouter()
MODEL_PATH = Path("artifacts/moisture_model.pkl")
METADATA_PATH = Path("artifacts/model_metadata.json")
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database_ready = False
    try:
        get_engine()
        database_ready = True
    except Exception:
        database_ready = False

    return HealthResponse(
        status="ok",
        model_loaded=MODEL_PATH.exists() and METADATA_PATH.exists(),
        database_ready=database_ready,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model artifacts are missing. Run training before calling /predict.",
        )

    service = RecommendationService(model_path=MODEL_PATH, metadata_path=METADATA_PATH)
    try:
        return service.predict_recommendation(request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc


@router.post("/api/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(request: FeedbackCreateRequest) -> FeedbackResponse:
    try:
        feedback_id, duplicate_prevented = create_feedback(request)
    except Exception as exc:
        logger.exception("Failed to store farmer feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {exc}",
        ) from exc

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
) -> RegionalInsights:
    try:
        insights = get_regional_insights(
            lat=lat,
            lon=lon,
            crop_type=crop_type or "",
            recommendation_type=recommendation_type or "",
            radius_km=radius,
        )
        return RegionalInsights(**insights)
    except Exception as exc:
        logger.exception("Failed to aggregate nearby feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nearby feedback lookup failed: {exc}",
        ) from exc
