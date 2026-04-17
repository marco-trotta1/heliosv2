from __future__ import annotations

import pandas as pd


SOIL_TEXTURES = ["sand", "loam", "clay"]
DRAINAGE_CLASSES = ["poor", "moderate", "well"]
IRRIGATION_TYPES = ["pivot", "drip", "flood"]
GROWTH_STAGES = ["emergence", "vegetative", "flowering", "grain_fill", "maturity"]
CROP_TYPES = ["corn", "soybean", "alfalfa", "potato"]

CROP_KC = {
    "emergence": 0.3,
    "vegetative": 0.7,
    "flowering": 1.15,
    "grain_fill": 1.0,
    "maturity": 0.5,
}

ROOT_ZONE_DEPTH_IN = {
    "sand": 11.811,
    "loam": 17.717,
    "clay": 19.685,
}

IRRIGATION_EFFICIENCY = {
    "pivot": 0.82,
    "drip": 0.93,
    "flood": 0.68,
}

DRAINAGE_FACTOR = {
    "poor": 0.75,
    "moderate": 1.0,
    "well": 1.15,
}

INCHES_PER_MM = 0.039370


def load_openet_monthly_et(openet_csv: str | None) -> dict[int, float]:
    if openet_csv is None:
        return {}
    df = pd.read_csv(openet_csv, parse_dates=["date"])
    lookup: dict[int, float] = {}
    for _, row in df.iterrows():
        daily_in = (float(row["openet_et_mm"]) / row["date"].days_in_month) * INCHES_PER_MM
        lookup[int(row["date"].month)] = round(daily_in, 4)
    return lookup
