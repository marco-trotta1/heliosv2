from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from helios.agronomy import CROP_KC, DRAINAGE_FACTOR, IRRIGATION_EFFICIENCY, ROOT_ZONE_DEPTH_IN
from helios.scripts.training_shared import (
    CROP_TYPES,
    DRAINAGE_CLASSES,
    GROWTH_STAGES,
    IRRIGATION_TYPES,
    SOIL_TEXTURES,
)
from helios.utils.evapotranspiration import estimate_reference_et_in
from helios.utils.openet import DEFAULT_OPENET_MONTHLY_ET_IN

TARGET_PROVENANCE_BY_SOURCE = {
    "synthetic_pyfao56": "pyfao56_simulated",
    "synthetic_fao56_season": "fao56_season_simulated",
}


def _engine_used(engine: str) -> str:
    if engine == "internal_fao56":
        return "internal_fao56"
    if engine == "pyfao56":
        return "pyfao56"
    if engine != "auto":
        raise ValueError("engine must be one of: auto, pyfao56, internal_fao56")

    try:
        __import__("pyfao56")
    except ImportError:
        return "internal_fao56"
    return "pyfao56"


def _source_id_for_engine(engine_used: str) -> str:
    return "synthetic_pyfao56" if engine_used == "pyfao56" else "synthetic_fao56_season"


def generate_simulated_seasons(
    *,
    seasons: int,
    seed: int,
    engine: str = "auto",
    days: int = 96,
) -> pd.DataFrame:
    if seasons < 1:
        raise ValueError("seasons must be at least 1.")
    if days < 4:
        raise ValueError("days must be at least 4 to create 72-hour labels.")

    rng = np.random.default_rng(seed)
    engine_used = _engine_used(engine)
    records: list[dict[str, float | int | str]] = []
    start = date(2026, 4, 1)

    for season_index in range(seasons):
        field_id = f"sim-field-{season_index:03d}"
        soil_texture = str(rng.choice(SOIL_TEXTURES))
        drainage_class = str(rng.choice(DRAINAGE_CLASSES))
        irrigation_type = str(rng.choice(IRRIGATION_TYPES))
        crop_type = str(rng.choice(CROP_TYPES))
        root_depth = ROOT_ZONE_DEPTH_IN[soil_texture]
        drainage = DRAINAGE_FACTOR[drainage_class]
        irrigation_efficiency = IRRIGATION_EFFICIENCY[irrigation_type]
        texture_start = {"sand": 0.18, "loam": 0.25, "clay": 0.32}[soil_texture]
        moisture = float(np.clip(texture_start + rng.normal(0.0, 0.025), 0.08, 0.46))
        lag_1 = float(np.clip(moisture + rng.normal(0.0, 0.012), 0.05, 0.50))
        lag_2 = float(np.clip(lag_1 + rng.normal(0.0, 0.012), 0.05, 0.50))
        irrigation_carryover: list[float] = []

        for day_index in range(days):
            current_date = start + timedelta(days=day_index)
            season_month = current_date.month
            growth_stage = GROWTH_STAGES[min(day_index * len(GROWTH_STAGES) // days, len(GROWTH_STAGES) - 1)]
            temperature_f = float(72.0 + 13.0 * np.sin(day_index / days * np.pi) + rng.normal(0.0, 4.5))
            humidity_pct = float(np.clip(54.0 - 10.0 * np.sin(day_index / days * np.pi) + rng.normal(0.0, 8.0), 18.0, 92.0))
            wind_mph = float(np.clip(rng.normal(7.0, 2.0), 1.0, 18.0))
            solar_radiation_mj_m2 = float(np.clip(20.0 + 5.0 * np.sin(day_index / days * np.pi) + rng.normal(0.0, 2.0), 8.0, 34.0))
            precipitation_in = float(np.clip(rng.gamma(0.8, 0.08) - 0.035, 0.0, 0.65))
            irrigation_today = 0.0
            if moisture < {"sand": 0.16, "loam": 0.22, "clay": 0.28}[soil_texture] or rng.random() < 0.08:
                irrigation_today = float(np.clip(rng.normal(0.42, 0.12), 0.12, 0.80))

            reference_et_in = estimate_reference_et_in(
                temperature_f=temperature_f,
                humidity_pct=humidity_pct,
                wind_mph=wind_mph,
                solar_radiation_mj_m2=solar_radiation_mj_m2,
            )
            kc = CROP_KC[growth_stage]
            et_depletion = (reference_et_in * kc * drainage) / root_depth
            precip_gain = precipitation_in * 0.88 / root_depth
            irrigation_gain = irrigation_today * irrigation_efficiency / root_depth
            next_moisture = float(np.clip(moisture - et_depletion + precip_gain + irrigation_gain, 0.05, 0.50))
            irrigation_carryover.append(irrigation_today)
            recent_24h = float(irrigation_today)
            recent_72h = float(sum(irrigation_carryover[-3:]))
            spread = {"sand": 0.045, "loam": 0.03, "clay": 0.02}[soil_texture]
            moisture_min = float(np.clip(moisture - spread / 2.0, 0.05, 0.50))
            moisture_max = float(np.clip(moisture + spread / 2.0, 0.05, 0.50))

            records.append(
                {
                    "engine_used": engine_used,
                    "field_id": field_id,
                    "date": pd.Timestamp(current_date),
                    "day_index": day_index,
                    "soil_moisture": round(moisture, 4),
                    "soil_moisture_lag_1": round(lag_1, 4),
                    "soil_moisture_lag_2": round(lag_2, 4),
                    "temperature_f": round(temperature_f, 3),
                    "humidity_pct": round(humidity_pct, 3),
                    "wind_mph": round(wind_mph, 3),
                    "precipitation_in": round(precipitation_in, 4),
                    "solar_radiation_mj_m2": round(solar_radiation_mj_m2, 3),
                    "reference_et_in": round(reference_et_in, 4),
                    "cumulative_irrigation_24h": round(recent_24h, 4),
                    "cumulative_irrigation_72h": round(recent_72h, 4),
                    "soil_texture": soil_texture,
                    "drainage_class": drainage_class,
                    "irrigation_type": irrigation_type,
                    "crop_type": crop_type,
                    "growth_stage": growth_stage,
                    "infiltration_rate_in_per_hour": round({"sand": 0.9, "loam": 0.5, "clay": 0.25}[soil_texture], 4),
                    "slope_pct": round(float(np.clip(rng.normal(2.4, 1.2), 0.0, 8.0)), 3),
                    "pump_capacity_in_per_hour": round(float(np.clip(rng.normal(0.26, 0.06), 0.08, 0.47)), 4),
                    "water_rights_schedule_count": int(rng.integers(1, 4)),
                    "energy_window_count": int(rng.integers(1, 3)),
                    "max_irrigation_volume_in": round(float(np.clip(rng.normal(0.72, 0.15), 0.25, 1.2)), 4),
                    "field_area_acres": round(float(np.clip(rng.normal(70.0, 22.0), 10.0, 150.0)), 3),
                    "budget_dollars": round(float(np.clip(rng.normal(650.0, 180.0), 100.0, 1300.0)), 3),
                    "moisture_min": round(moisture_min, 4),
                    "moisture_max": round(moisture_max, 4),
                    "moisture_mean": round((moisture_min + moisture_max) / 2.0, 4),
                    "moisture_spread": round(moisture_max - moisture_min, 4),
                    "physical_sensor_count": 2,
                    "sensor_count": 2,
                    "season_month": season_month,
                    "openet_monthly_et_in": DEFAULT_OPENET_MONTHLY_ET_IN.get(season_month, 0.1),
                }
            )
            lag_2 = lag_1
            lag_1 = moisture
            moisture = next_moisture

    return pd.DataFrame.from_records(records)


def seasons_to_training_rows(
    seasons: pd.DataFrame,
    *,
    source_id: str | None = None,
) -> pd.DataFrame:
    if seasons.empty:
        return pd.DataFrame()

    training_rows: list[dict[str, float | int | str]] = []
    for _, group in seasons.sort_values(["field_id", "date"]).groupby("field_id", sort=True):
        group = group.reset_index(drop=True)
        for index in range(0, len(group) - 3):
            origin = group.iloc[index]
            plus_1 = group.iloc[index + 1]
            plus_2 = group.iloc[index + 2]
            plus_3 = group.iloc[index + 3]
            row_source = source_id or _source_id_for_engine(str(origin["engine_used"]))
            target_source = TARGET_PROVENANCE_BY_SOURCE[row_source]
            current = float(origin["soil_moisture"])
            lag_1 = float(origin["soil_moisture_lag_1"])
            lag_2 = float(origin["soil_moisture_lag_2"])
            training_rows.append(
                {
                    "source_id": row_source,
                    "field_id": str(origin["field_id"]),
                    "prediction_time": str(origin["date"]),
                    "forecast_horizon_hours": 72,
                    "temperature_f": origin["temperature_f"],
                    "humidity_pct": origin["humidity_pct"],
                    "wind_mph": origin["wind_mph"],
                    "precipitation_in": origin["precipitation_in"],
                    "solar_radiation_mj_m2": origin["solar_radiation_mj_m2"],
                    "rolling_temp_mean": origin["temperature_f"],
                    "rolling_humidity_mean": origin["humidity_pct"],
                    "rolling_precip_in": origin["precipitation_in"],
                    "rolling_solar_mean": origin["solar_radiation_mj_m2"],
                    "current_soil_moisture": round(current, 4),
                    "soil_moisture_lag_1": round(lag_1, 4),
                    "soil_moisture_lag_2": round(lag_2, 4),
                    "soil_moisture_delta_1": round(current - lag_1, 4),
                    "soil_moisture_delta_2": round(lag_1 - lag_2, 4),
                    "moisture_min": origin["moisture_min"],
                    "moisture_max": origin["moisture_max"],
                    "moisture_mean": origin["moisture_mean"],
                    "moisture_spread": origin["moisture_spread"],
                    "physical_sensor_count": origin["physical_sensor_count"],
                    "pump_capacity_in_per_hour": origin["pump_capacity_in_per_hour"],
                    "water_rights_schedule_count": origin["water_rights_schedule_count"],
                    "energy_window_count": origin["energy_window_count"],
                    "irrigation_type": origin["irrigation_type"],
                    "soil_texture": origin["soil_texture"],
                    "infiltration_rate_in_per_hour": origin["infiltration_rate_in_per_hour"],
                    "slope_pct": origin["slope_pct"],
                    "drainage_class": origin["drainage_class"],
                    "crop_type": origin["crop_type"],
                    "growth_stage": origin["growth_stage"],
                    "max_irrigation_volume_in": origin["max_irrigation_volume_in"],
                    "field_area_acres": origin["field_area_acres"],
                    "budget_dollars": origin["budget_dollars"],
                    "cumulative_irrigation_24h": origin["cumulative_irrigation_24h"],
                    "cumulative_irrigation_72h": origin["cumulative_irrigation_72h"],
                    "sensor_count": origin["sensor_count"],
                    "season_month": origin["season_month"],
                    "openet_monthly_et_in": origin["openet_monthly_et_in"],
                    "reference_et_in": origin["reference_et_in"],
                    "target_moisture_24h": plus_1["soil_moisture"],
                    "target_moisture_48h": plus_2["soil_moisture"],
                    "target_moisture_72h": plus_3["soil_moisture"],
                    "target_source_24h": target_source,
                    "target_source_48h": target_source,
                    "target_source_72h": target_source,
                }
            )

    return pd.DataFrame.from_records(training_rows)
