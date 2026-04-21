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
    driving_zone: str
    zone_moisture_summary: dict[str, float]
    high_variability_flag: bool


class RegionalInsights(BaseModel):
    success_rate: float = Field(ge=0, le=1)
    avg_yield_delta: float | None = None
    total_samples: int = Field(ge=0)
    weighted_samples: float = Field(ge=0)
    comparable_samples: int = Field(ge=0)
    radius_miles: float = Field(gt=0)


class RecommendationAdjustment(BaseModel):
    base_recommendation_in: float = Field(ge=0)
    adjusted_recommendation_in: float = Field(ge=0)
    adjustment_factor: float = Field(gt=0)
    reason: str


class PredictionResponse(BaseModel):
    decision: Literal["water", "wait"]
    recommended_amount_in: float = Field(ge=0)
    timing_window: str
    confidence_score: float = Field(ge=0, le=1)
    et_source: str | None = None
    explanation: RecommendationExplanation
    predicted_moisture: MoistureForecast
    regional_insights: RegionalInsights | None = None
    recommendation_adjustment: RecommendationAdjustment | None = None


class HealthResponse(BaseModel):
    status: Literal["ready", "degraded"]
    ready: bool
    model_loaded: bool
    database_ready: bool
    rate_limit_enabled: bool
    timestamp: datetime
    issues: list[str] = Field(default_factory=list)


class FeedbackResponse(BaseModel):
    id: int
    duplicate_prevented: bool = False
    message: str


class ErrorResponse(BaseModel):
    error_code: str
    detail: str
    issues: list[str] = Field(default_factory=list)
