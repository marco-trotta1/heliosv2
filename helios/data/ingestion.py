from __future__ import annotations

from typing import Any

import pandas as pd

from helios.schemas.inputs import IrrigationEventInput, PredictionRequest, SoilMoistureReading
from helios.utils.openet import DEFAULT_OPENET_MONTHLY_ET_IN

def soil_moisture_series_to_frame(readings: list[SoilMoistureReading]) -> pd.DataFrame:
    frame = pd.DataFrame([reading.model_dump() for reading in readings])
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "field_id", "sensor_id", "volumetric_water_content"])
    return frame.sort_values(["timestamp", "sensor_id"]).reset_index(drop=True)


def irrigation_events_to_frame(events: list[IrrigationEventInput]) -> pd.DataFrame:
    frame = pd.DataFrame([event.model_dump() for event in events])
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "applied_in"])
    return frame.sort_values("timestamp").reset_index(drop=True)


def _safe_get(series: pd.Series, index: int, fallback: float) -> float:
    try:
        return float(series.iloc[index])
    except IndexError:
        return fallback


def fallback_openet_monthly_et_in(month: int) -> float:
    return DEFAULT_OPENET_MONTHLY_ET_IN.get(month, DEFAULT_OPENET_MONTHLY_ET_IN[8])


def request_to_feature_frame(
    request: PredictionRequest,
    *,
    openet_monthly_et_in: float | None = None,
) -> pd.DataFrame:
    readings_df = soil_moisture_series_to_frame(request.soil_moisture_readings)
    irrigation_df = irrigation_events_to_frame(request.recent_irrigation_events)
    sensor_snapshots: dict[str, dict[str, float]] = {}
    for sensor_id, sensor_frame in readings_df.groupby("sensor_id", sort=True):
        moisture_series = sensor_frame["volumetric_water_content"].astype(float)
        current_vwc = _safe_get(moisture_series, -1, 0.0)
        lag_1 = _safe_get(moisture_series, -2, current_vwc)
        lag_2 = _safe_get(moisture_series, -3, lag_1)
        sensor_snapshots[str(sensor_id)] = {
            "current_vwc": current_vwc,
            "lag_1": lag_1,
            "lag_2": lag_2,
        }

    primary_sensor_id, primary_sensor = min(
        sensor_snapshots.items(),
        key=lambda item: (item[1]["current_vwc"], item[0]),
    )
    current_values = [sensor["current_vwc"] for sensor in sensor_snapshots.values()]
    moisture_min = min(current_values)
    moisture_max = max(current_values)
    moisture_mean = float(sum(current_values) / len(current_values))
    moisture_spread = moisture_max - moisture_min
    physical_sensor_count = len(sensor_snapshots)

    current_moisture = primary_sensor["current_vwc"]
    lag_1 = primary_sensor["lag_1"]
    lag_2 = primary_sensor["lag_2"]

    latest_timestamp = readings_df["timestamp"].iloc[-1]
    latest_ts_dt = pd.to_datetime(latest_timestamp, utc=True)
    season_month = latest_ts_dt.month
    resolved_openet_monthly_et_in = (
        fallback_openet_monthly_et_in(season_month)
        if openet_monthly_et_in is None
        else openet_monthly_et_in
    )

    irrigation_24h = 0.0
    irrigation_72h = 0.0
    if not irrigation_df.empty:
        irrigation_df = irrigation_df.copy()
        irrigation_df["timestamp"] = pd.to_datetime(irrigation_df["timestamp"], utc=True)
        latest_timestamp = pd.to_datetime(latest_timestamp, utc=True)
        irrigation_24h = float(
            irrigation_df.loc[
                irrigation_df["timestamp"] >= latest_timestamp - pd.Timedelta(hours=24),
                "applied_in",
            ].sum()
        )
        irrigation_72h = float(
            irrigation_df.loc[
                irrigation_df["timestamp"] >= latest_timestamp - pd.Timedelta(hours=72),
                "applied_in",
            ].sum()
        )

    record: dict[str, Any] = {
        "field_id": request.field_id,
        "forecast_horizon_hours": request.forecast_horizon_hours,
        "temperature_f": request.weather.temperature_f,
        "humidity_pct": request.weather.humidity_pct,
        "wind_mph": request.weather.wind_mph,
        "precipitation_in": request.weather.precipitation_in,
        "solar_radiation_mj_m2": request.weather.solar_radiation_mj_m2,
        "rolling_temp_mean": request.weather.temperature_f,
        "rolling_humidity_mean": request.weather.humidity_pct,
        "rolling_precip_in": request.weather.precipitation_in,
        "rolling_solar_mean": request.weather.solar_radiation_mj_m2,
        "current_soil_moisture": current_moisture,
        "soil_moisture_lag_1": lag_1,
        "soil_moisture_lag_2": lag_2,
        "soil_moisture_delta_1": current_moisture - lag_1,
        "soil_moisture_delta_2": lag_1 - lag_2,
        "moisture_min": moisture_min,
        "moisture_max": moisture_max,
        "moisture_mean": moisture_mean,
        "moisture_spread": moisture_spread,
        "physical_sensor_count": physical_sensor_count,
        "pump_capacity_in_per_hour": request.irrigation_system.pump_capacity_in_per_hour,
        "water_rights_schedule_count": len(request.irrigation_system.water_rights_schedule),
        "energy_window_count": len(request.irrigation_system.energy_price_window),
        "irrigation_type": request.irrigation_system.irrigation_type,
        "soil_texture": request.soil_properties.soil_texture,
        "infiltration_rate_in_per_hour": request.soil_properties.infiltration_rate_in_per_hour,
        "slope_pct": request.soil_properties.slope_pct,
        "drainage_class": request.soil_properties.drainage_class,
        "crop_type": request.crop.crop_type,
        "growth_stage": request.crop.growth_stage,
        "max_irrigation_volume_in": request.operational.max_irrigation_volume_in,
        "field_area_acres": request.operational.field_area_acres,
        "budget_dollars": request.operational.budget_dollars,
        "cumulative_irrigation_24h": irrigation_24h,
        "cumulative_irrigation_72h": irrigation_72h,
        "sensor_count": physical_sensor_count,
        "primary_sensor_id": primary_sensor_id,
        "season_month": season_month,
        "openet_monthly_et_in": resolved_openet_monthly_et_in,
    }
    return pd.DataFrame([record])
