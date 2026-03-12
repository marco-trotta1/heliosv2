from __future__ import annotations

from typing import Any, Protocol

from helios.schemas.inputs import WeatherInput


class WeatherProviderProtocol(Protocol):
    def get_weather(self, weather: WeatherInput) -> dict[str, Any]:
        """Return a normalized weather snapshot."""


class StaticWeatherProvider:
    """Local stub provider designed to be replaced by NOAA integration later."""

    def get_weather(self, weather: WeatherInput) -> dict[str, Any]:
        return weather.model_dump()


def fetch_weather_snapshot(
    weather: WeatherInput,
    provider: WeatherProviderProtocol | None = None,
) -> dict[str, Any]:
    active_provider = provider or StaticWeatherProvider()
    return active_provider.get_weather(weather)
