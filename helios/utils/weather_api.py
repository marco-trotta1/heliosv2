from __future__ import annotations

from datetime import datetime
import re
from typing import Any

import httpx

# Solar radiation is not available from NOAA hourly forecasts.
# This monthly climatological estimate is derived from NASA POWER data
# for ~43.6°N (Snake River Plain, Idaho). It is an approximation.
# Replace with measured pyranometer data when available.
IDAHO_SOLAR_MJ_M2 = {
    1: 7.5,
    2: 10.8,
    3: 15.2,
    4: 19.8,
    5: 23.4,
    6: 26.1,
    7: 26.8,
    8: 23.9,
    9: 18.7,
    10: 12.4,
    11: 7.8,
    12: 6.2,
}
NOAA_HEADERS = {
    "Accept": "application/geo+json, application/json",
    "User-Agent": "Helios/0.2.0 (NOAA weather enrichment)",
}
NOAA_TIMEOUT_SECONDS = 10.0


def _seasonal_solar_radiation() -> float:
    month = datetime.now().month
    return IDAHO_SOLAR_MJ_M2[month]


def _parse_wind_mph(wind_speed: str) -> float:
    numeric_parts = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", wind_speed or "")]
    if not numeric_parts:
        raise ValueError("NOAA forecast is missing a parseable windSpeed value")
    return round(sum(numeric_parts) / len(numeric_parts), 2)


def fetch_noaa_weather(lat: float, lon: float) -> dict[str, Any]:
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    try:
        points_response = httpx.get(points_url, headers=NOAA_HEADERS, timeout=NOAA_TIMEOUT_SECONDS)
        points_response.raise_for_status()
        forecast_hourly_url = points_response.json()["properties"]["forecastHourly"]

        forecast_response = httpx.get(forecast_hourly_url, headers=NOAA_HEADERS, timeout=NOAA_TIMEOUT_SECONDS)
        forecast_response.raise_for_status()
        period = forecast_response.json()["properties"]["periods"][0]
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch NOAA weather for ({lat}, {lon}): {exc}") from exc

    try:
        temperature_f = float(period["temperature"])
        humidity_pct = float(period["relativeHumidity"]["value"])
        wind_mph = _parse_wind_mph(period["windSpeed"])
        precipitation_probability = float(period.get("probabilityOfPrecipitation", {}).get("value") or 0.0)
        return {
            "temperature_f": temperature_f,
            "humidity_pct": humidity_pct,
            "wind_mph": wind_mph,
            "precipitation_in": 0.1 if precipitation_probability > 50 else 0.0,
            "solar_radiation_mj_m2": _seasonal_solar_radiation(),
            "forecast_horizon_hours": 72,
        }
    except Exception as exc:
        raise RuntimeError(f"NOAA response for ({lat}, {lon}) was missing required weather fields: {exc}") from exc
