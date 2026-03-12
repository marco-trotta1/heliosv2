from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from helios.database.db import get_engine
from helios.schemas.inputs import PredictionRequest
from helios.schemas.outputs import HealthResponse, PredictionResponse
from helios.services.recommendation_service import RecommendationService


router = APIRouter()
MODEL_PATH = Path("artifacts/moisture_model.pkl")
METADATA_PATH = Path("artifacts/model_metadata.json")


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
