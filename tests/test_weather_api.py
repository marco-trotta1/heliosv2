from __future__ import annotations

from datetime import datetime

import httpx
import pytest

import helios.utils.weather_api as weather_api
from helios.utils.weather_api import fetch_noaa_weather


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_fetch_noaa_weather_returns_normalized_weather(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        FakeResponse(
            {
                "properties": {
                    "forecastHourly": "https://api.weather.gov/gridpoints/BOI/1,1/forecast/hourly",
                }
            }
        ),
        FakeResponse(
            {
                "properties": {
                    "periods": [
                        {
                            "startTime": "2026-03-17T12:00:00-06:00",
                            "temperature": 72,
                            "relativeHumidity": {"value": 41},
                            "windSpeed": "5 to 10 mph",
                            "probabilityOfPrecipitation": {"value": 80},
                        }
                    ]
                }
            }
        ),
    ]

    def fake_get(url: str, **_: object) -> FakeResponse:
        return responses.pop(0)

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(
        weather_api,
        "datetime",
        type("FrozenDatetime", (), {"now": classmethod(lambda cls: datetime(2026, 3, 17, 12, 0, 0))}),
    )

    result = fetch_noaa_weather(43.615, -116.202)

    assert result == {
        "temperature_f": 72.0,
        "humidity_pct": 41.0,
        "wind_mph": 7.5,
        "precipitation_in": 0.1,
        "solar_radiation_mj_m2": 15.2,
        "forecast_horizon_hours": 72,
    }


def test_fetch_noaa_weather_raises_descriptive_error(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://api.weather.gov/points/43.615,-116.202")

    def fake_get(url: str, **_: object) -> FakeResponse:
        raise httpx.RequestError("boom", request=request)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Failed to fetch NOAA weather"):
        fetch_noaa_weather(43.615, -116.202)
