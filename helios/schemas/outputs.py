from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MoistureForecast(BaseModel):
    moisture_24h: float = Field(ge=0, le=1)
    moisture_48h: float = Field(ge=0, le=1)
    moisture_72h: float = Field(ge=0, le=1)


class RecommendationExplanation(BaseModel):
    predicted_moisture_48h: float = Field(ge=0, le=1)
    stress_probability: float = Field(ge=0, le=1)
    drivers: list[str]


class PredictionResponse(BaseModel):
    decision: Literal["water", "wait"]
    recommended_amount_mm: float = Field(ge=0)
    timing_window: str
    confidence_score: float = Field(ge=0, le=1)
    explanation: RecommendationExplanation
    predicted_moisture: MoistureForecast


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
    database_ready: bool
    timestamp: datetime


class ChartPoint(BaseModel):
    label: str
    moisture: float = Field(ge=0, le=1)
