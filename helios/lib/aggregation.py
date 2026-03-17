from __future__ import annotations

import math
from typing import Any


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance for nearby-farm weighting."""
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def distance_weight(distance_km: float, radius_km: float) -> float:
    if radius_km <= 0:
        return 0.0
    return max(0.1, 1 - (distance_km / radius_km))


def aggregate_feedback(
    rows: list[dict[str, Any]],
    *,
    origin_lat: float,
    origin_lon: float,
    radius_km: float,
) -> dict[str, float | int | None]:
    filtered: list[tuple[dict[str, Any], float]] = []
    for row in rows:
        distance = haversine_km(origin_lat, origin_lon, row["location_lat"], row["location_lon"])
        if distance <= radius_km:
            filtered.append((row, distance))

    if not filtered:
        return {
            "success_rate": 0.0,
            "avg_yield_delta": None,
            "total_samples": 0,
            "weighted_samples": 0.0,
            "radius_km": radius_km,
        }

    weighted_success = 0.0
    total_weight = 0.0
    weighted_yield_sum = 0.0
    weighted_yield_weight = 0.0

    for row, distance in filtered:
        weight = distance_weight(distance, radius_km)
        outcome_score = {"SUCCESS": 1.0, "PARTIAL": 0.5, "FAILURE": 0.0}.get(row["outcome"], 0.0)
        weighted_success += weight * outcome_score
        total_weight += weight
        if row.get("yield_delta") is not None:
            weighted_yield_sum += weight * float(row["yield_delta"])
            weighted_yield_weight += weight

    return {
        "success_rate": round(weighted_success / total_weight, 3) if total_weight else 0.0,
        "avg_yield_delta": round(weighted_yield_sum / weighted_yield_weight, 3) if weighted_yield_weight else None,
        "total_samples": len(filtered),
        "weighted_samples": round(total_weight, 3),
        "radius_km": radius_km,
    }
