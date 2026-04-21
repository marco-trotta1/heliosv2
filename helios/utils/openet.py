from __future__ import annotations

import calendar
import logging
import os
from datetime import date, datetime

import requests

logger = logging.getLogger(__name__)

OPENET_ENDPOINT = "https://openet-api.org/raster/timeseries/point"
INCHES_PER_MM = 0.039370
OPENET_TIMEOUT_SECONDS = 6.0
DEFAULT_OPENET_MONTHLY_ET_IN = {
    4: 0.1024,
    5: 0.0991,
    6: 0.1024,
    7: 0.1080,
    8: 0.0876,
    9: 0.0289,
}
_OPENET_MONTHLY_CACHE: dict[tuple[float, float, int, int], float] = {}


def fetch_monthly_et(
    longitude: float,
    latitude: float,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch monthly ensemble ET from OpenET for a single point.

    Parameters
    ----------
    longitude:
        Decimal degrees, WGS84.
    latitude:
        Decimal degrees, WGS84.
    start_date:
        ISO date string, e.g. "2022-04-01".
    end_date:
        ISO date string, e.g. "2022-09-30".

    Returns
    -------
    list[dict]
        Parsed JSON list returned by the OpenET API.

    Raises
    ------
    RuntimeError
        If OPENET_API_KEY is not set, or if the API returns a non-200 status.
    """
    api_key = os.environ.get("OPENET_API_KEY")
    if not api_key:
        raise RuntimeError("OPENET_API_KEY environment variable is not set")

    payload = {
        "date_range": [start_date, end_date],
        "geometry": [longitude, latitude],
        "model": "Ensemble",
        "variable": "ET",
        "reference_et": "gridMET",
        "units": "mm",
        "interval": "monthly",
        "file_format": "JSON",
    }
    headers = {"Authorization": api_key}

    try:
        response = requests.post(OPENET_ENDPOINT, json=payload, headers=headers, timeout=OPENET_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenET API request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "OpenET request failed: status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(
            f"OpenET API returned status {response.status_code}: {response.text}"
        )

    return response.json()


def clear_openet_cache() -> None:
    _OPENET_MONTHLY_CACHE.clear()


def _month_bounds(observed_at: datetime | date) -> tuple[str, str]:
    year = observed_at.year
    month = observed_at.month
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1).isoformat()
    end_date = date(year, month, last_day).isoformat()
    return start_date, end_date


def _fallback_monthly_et_in(month: int) -> float:
    return DEFAULT_OPENET_MONTHLY_ET_IN.get(month, DEFAULT_OPENET_MONTHLY_ET_IN[8])


def _extract_monthly_et_in(records: list[dict], year: int, month: int) -> float | None:
    days_in_month = calendar.monthrange(year, month)[1]
    for record in records:
        raw_time = record.get("time") or record.get("date")
        if raw_time is None:
            continue
        try:
            observed_at = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
        except ValueError:
            continue
        if observed_at.year != year or observed_at.month != month:
            continue
        monthly_mm = record.get("et")
        if monthly_mm is None:
            continue
        return round((float(monthly_mm) / days_in_month) * INCHES_PER_MM, 4)
    return None


def resolve_monthly_et_in(
    *,
    longitude: float,
    latitude: float,
    observed_at: datetime,
) -> tuple[float, str]:
    month = observed_at.month
    fallback_value = _fallback_monthly_et_in(month)
    api_key = os.environ.get("OPENET_API_KEY")
    if not api_key:
        return fallback_value, "openet-fallback"

    cache_key = (round(longitude, 3), round(latitude, 3), observed_at.year, observed_at.month)
    cached_value = _OPENET_MONTHLY_CACHE.get(cache_key)
    if cached_value is not None:
        return cached_value, "openet-cache"

    start_date, end_date = _month_bounds(observed_at)
    try:
        records = fetch_monthly_et(
            longitude=cache_key[0],
            latitude=cache_key[1],
            start_date=start_date,
            end_date=end_date,
        )
    except RuntimeError as exc:
        logger.warning("OpenET runtime lookup failed; using fallback ET. error=%s", exc)
        return fallback_value, "openet-fallback"

    monthly_et_in = _extract_monthly_et_in(records, observed_at.year, observed_at.month)
    if monthly_et_in is None:
        logger.warning(
            "OpenET runtime lookup returned no matching monthly ET; using fallback. year=%s month=%s",
            observed_at.year,
            observed_at.month,
        )
        return fallback_value, "openet-fallback"

    _OPENET_MONTHLY_CACHE[cache_key] = monthly_et_in
    return monthly_et_in, "openet-live"
