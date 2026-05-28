from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

import requests

from helios.utils.openet import OPENET_ENDPOINT, OPENET_TIMEOUT_SECONDS


DATE_KEYS = ("date", "time", "start_date", "start")
ET_KEYS = ("openet_et_mm", "et", "ET", "Ensemble", "ensemble")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch monthly OpenET ET point data and write a CSV.")
    parser.add_argument("--start-date", required=True, help="Start date, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date, YYYY-MM-DD")
    parser.add_argument("--longitude", type=float, required=True, help="Point longitude, WGS84 decimal degrees")
    parser.add_argument("--latitude", type=float, required=True, help="Point latitude, WGS84 decimal degrees")
    parser.add_argument("--output", required=True, help="Output CSV path")
    return parser.parse_args()


def _response_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("data", "results", "features"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                rows = candidate
                break
        if rows is None:
            rows = [payload]
    else:
        raise RuntimeError(f"Unexpected OpenET response type: {type(payload).__name__}")

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Unexpected OpenET response row; expected an object.")
        properties = row.get("properties")
        if isinstance(properties, dict):
            merged = {key: value for key, value in row.items() if key != "properties"}
            merged.update(properties)
            normalized.append(merged)
        else:
            normalized.append(row)
    return normalized


def _first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    lower_lookup = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        value = lower_lookup.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def normalize_openet_rows(payload: Any) -> list[dict[str, Any]]:
    rows = _response_rows(payload)
    output_rows: list[dict[str, Any]] = []

    for row in rows:
        raw_date = _first_present(row, DATE_KEYS)
        raw_et = _first_present(row, ET_KEYS)
        if raw_date is None or raw_et is None:
            raise RuntimeError(
                "Unexpected OpenET response format; each row must include a date/time and ET value."
            )
        try:
            openet_et_mm = float(raw_et)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"OpenET ET value is not numeric: {raw_et!r}") from exc

        normalized = dict(row)
        normalized["date"] = str(raw_date)[:10]
        normalized["openet_et_mm"] = openet_et_mm
        output_rows.append(normalized)

    if not output_rows:
        raise RuntimeError("OpenET returned no rows.")
    return output_rows


def fetch_openet_monthly(
    *,
    start_date: str,
    end_date: str,
    longitude: float,
    latitude: float,
) -> list[dict[str, Any]]:
    api_key = os.environ.get("OPENET_API_KEY")
    if not api_key:
        raise RuntimeError("OPENET_API_KEY environment variable is not set.")

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
        response = requests.post(
            OPENET_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=OPENET_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenET API request failed: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"OpenET API returned status {response.status_code}: {response.text}")

    try:
        return normalize_openet_rows(response.json())
    except ValueError as exc:
        raise RuntimeError(f"OpenET response was not valid JSON: {exc}") from exc


def write_openet_csv(rows: list[dict[str, Any]], output_path: str) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["date", "openet_et_mm"]
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    try:
        rows = fetch_openet_monthly(
            start_date=args.start_date,
            end_date=args.end_date,
            longitude=args.longitude,
            latitude=args.latitude,
        )
        write_openet_csv(rows, args.output)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
