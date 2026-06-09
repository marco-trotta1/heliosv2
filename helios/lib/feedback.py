from __future__ import annotations

import math
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
DEFAULT_RADIUS_MILES = 31.07  # ~50 km in miles
# z for a ~90% confidence interval; used to require that the observed success rate is
# statistically distinguishable from the neutral 0.5 before nudging a recommendation.
WILSON_Z = 1.645
NEUTRAL_SUCCESS_RATE = 0.5


def _wilson_bounds(success_rate: float, n: float, z: float = WILSON_Z) -> tuple[float, float]:
    """Wilson score interval for a proportion, using effective (weighted) sample size n."""
    if n <= 0:
        return 0.0, 1.0
    denom = 1.0 + (z * z) / n
    center = success_rate + (z * z) / (2 * n)
    margin = z * math.sqrt(success_rate * (1 - success_rate) / n + (z * z) / (4 * n * n))
    return (center - margin) / denom, (center + margin) / denom


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
    radius_miles: float = DEFAULT_RADIUS_MILES,
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
        radius_miles=radius_miles,
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
            "adjusted_recommendation_in": round(base_recommendation, 2),
            "adjustment_factor": 1.0,
            "reason": "Not enough comparable nearby feedback to safely adjust the base recommendation.",
        }

    success_rate = float(insights["success_rate"])
    avg_yield_delta = insights.get("avg_yield_delta")
    effective_n = float(insights.get("weighted_samples", 0.0))
    lower_bound, upper_bound = _wilson_bounds(success_rate, effective_n)

    # Only nudge when the confidence interval clears the neutral midpoint — otherwise the
    # observed success rate is consistent with chance and an adjustment would be noise.
    if success_rate > 0.7 and lower_bound > NEUTRAL_SUCCESS_RATE:
        factor = 1.05 if avg_yield_delta is None or avg_yield_delta < 5 else 1.08
        reason = "Comparable nearby feedback was consistently positive, so the recommendation was modestly reinforced."
    elif success_rate < 0.4 and upper_bound < NEUTRAL_SUCCESS_RATE:
        factor = 0.92 if avg_yield_delta is None or avg_yield_delta > -5 else 0.88
        reason = "Comparable nearby feedback was weak, so the recommendation was reduced conservatively."
    else:
        factor = 1.0
        reason = (
            "Comparable nearby feedback was not statistically conclusive, "
            "so the base recommendation was left unchanged."
        )

    adjusted = max(0.0, round(base_recommendation * factor, 2))
    return {
        "adjusted_recommendation_in": adjusted,
        "adjustment_factor": round(factor, 3),
        "reason": reason,
    }
