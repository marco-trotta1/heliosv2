from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

OPENET_ENDPOINT = "https://openet-api.org/raster/timeseries/point"


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

    response = requests.post(OPENET_ENDPOINT, json=payload, headers=headers)
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
