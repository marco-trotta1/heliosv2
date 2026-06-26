from __future__ import annotations

import pandas as pd


# Training-schema vocabulary (one-hot categories + sampling domains). The agronomic
# constant tables (CROP_KC, ROOT_ZONE_DEPTH_IN, DRAINAGE_FACTOR, IRRIGATION_EFFICIENCY)
# now live in helios.agronomy — the single home for the water-balance physics.
SOIL_TEXTURES = ["sand", "loam", "clay"]
DRAINAGE_CLASSES = ["poor", "moderate", "well"]
IRRIGATION_TYPES = ["pivot", "drip", "flood"]
GROWTH_STAGES = ["emergence", "vegetative", "flowering", "grain_fill", "maturity"]
CROP_TYPES = ["corn", "soybean", "alfalfa", "potato"]

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
