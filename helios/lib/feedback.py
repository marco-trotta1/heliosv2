from __future__ import annotations

from datetime import timedelta
from typing import Any

from helios.database.db import (
    find_duplicate_feedback,
    get_feedback_rows,
    insert_feedback,
)
from helios.lib.aggregation import aggregate_feedback
from helios.schemas.inputs import FeedbackCreateRequest


DUPLICATE_WINDOW_MINUTES = 30
DEFAULT_RADIUS_KM = 50.0


def create_feedback(payload: FeedbackCreateRequest) -> tuple[int, bool]:
    duplicate_id = find_duplicate_feedback(
        farm_id=payload.farm_id,
        timestamp=payload.timestamp,
        recommendation_type=payload.recommendation_type,
        window=timedelta(minutes=DUPLICATE_WINDOW_MINUTES),
    )
    if duplicate_id is not None:
        return duplicate_id, True

    feedback_id = insert_feedback(payload)
    return feedback_id, False


def get_regional_insights(
    lat: float,
    lon: float,
    crop_type: str,
    recommendation_type: str,
    soil_texture: str,
    irrigation_type: str,
    growth_stage: str,
    season_month: int,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> dict[str, float | int | None]:
    rows = get_feedback_rows(
        crop_type=crop_type,
        recommendation_type=recommendation_type,
        soil_texture=soil_texture,
        irrigation_type=irrigation_type,
    )
    return aggregate_feedback(
        rows,
        origin_lat=lat,
        origin_lon=lon,
        radius_km=radius_km,
        growth_stage=growth_stage,
        season_month=season_month,
    )


def adjust_recommendation(
    base_recommendation: float,
    insights: dict[str, Any] | None,
) -> dict[str, float | str]:
    if (
        not insights
        or insights.get("total_samples", 0) < 4
        or insights.get("comparable_samples", 0) < 2
        or insights.get("weighted_samples", 0.0) < 2.5
    ):
        return {
            "adjusted_recommendation_mm": round(base_recommendation, 1),
            "adjustment_factor": 1.0,
            "reason": "Not enough comparable nearby feedback to safely adjust the base recommendation.",
        }

    success_rate = float(insights["success_rate"])
    avg_yield_delta = insights.get("avg_yield_delta")

    if success_rate > 0.7:
        factor = 1.05 if avg_yield_delta is None or avg_yield_delta < 5 else 1.08
        reason = "Comparable nearby feedback was consistently positive, so the recommendation was modestly reinforced."
    elif success_rate < 0.4:
        factor = 0.92 if avg_yield_delta is None or avg_yield_delta > -5 else 0.88
        reason = "Comparable nearby feedback was weak, so the recommendation was reduced conservatively."
    else:
        factor = 1.0
        reason = "Comparable nearby feedback was mixed, so the base recommendation was left unchanged."

    adjusted = max(0.0, round(base_recommendation * factor, 1))
    return {
        "adjusted_recommendation_mm": adjusted,
        "adjustment_factor": round(factor, 3),
        "reason": reason,
    }
