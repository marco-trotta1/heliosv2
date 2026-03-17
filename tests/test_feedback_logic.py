from __future__ import annotations

from helios.lib.aggregation import aggregate_feedback
from helios.lib.feedback import adjust_recommendation


def test_aggregate_feedback_applies_distance_and_comparability_weights() -> None:
    rows = [
        {
            "location_lat": 43.615,
            "location_lon": -116.202,
            "outcome": "SUCCESS",
            "yield_delta": 5.0,
            "growth_stage": "flowering",
            "season_month": 7,
        },
        {
            "location_lat": 44.50,
            "location_lon": -117.10,
            "outcome": "FAILURE",
            "yield_delta": -6.0,
            "growth_stage": "vegetative",
            "season_month": 10,
        },
    ]

    insights = aggregate_feedback(
        rows,
        origin_lat=43.615,
        origin_lon=-116.202,
        radius_km=50,
        growth_stage="flowering",
        season_month=7,
    )

    assert insights["total_samples"] == 1
    assert insights["comparable_samples"] == 1
    assert insights["success_rate"] == 1.0
    assert insights["avg_yield_delta"] == 5.0


def test_adjust_recommendation_requires_enough_comparable_samples() -> None:
    adjustment = adjust_recommendation(
        12.0,
        {
            "success_rate": 0.9,
            "avg_yield_delta": 8.0,
            "total_samples": 3,
            "weighted_samples": 2.4,
            "comparable_samples": 1,
        },
    )

    assert adjustment["adjusted_recommendation_mm"] == 12.0
    assert adjustment["adjustment_factor"] == 1.0


def test_adjust_recommendation_reinforces_and_reduces_conservatively() -> None:
    stronger = adjust_recommendation(
        10.0,
        {
            "success_rate": 0.82,
            "avg_yield_delta": 6.0,
            "total_samples": 6,
            "weighted_samples": 4.0,
            "comparable_samples": 4,
        },
    )
    weaker = adjust_recommendation(
        10.0,
        {
            "success_rate": 0.25,
            "avg_yield_delta": -8.0,
            "total_samples": 6,
            "weighted_samples": 4.0,
            "comparable_samples": 4,
        },
    )

    assert stronger["adjusted_recommendation_mm"] == 10.8
    assert weaker["adjusted_recommendation_mm"] == 8.8
