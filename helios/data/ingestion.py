from __future__ import annotations

from typing import Any

import pandas as pd

from helios.schemas.inputs import IrrigationEventInput, PredictionRequest, SoilMoistureReading


def soil_moisture_series_to_frame(readings: list[SoilMoistureReading]) -> pd.DataFrame:
    frame = pd.DataFrame([reading.model_dump() for reading in readings])
    if frame.empty:
        return frame
    return frame.sort_values("timestamp").reset_index(drop=True)


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


def request_to_feature_frame(request: PredictionRequest) -> pd.DataFrame:
    readings_df = soil_moisture_series_to_frame(request.soil_moisture_readings)
    irrigation_df = irrigation_events_to_frame(request.recent_irrigation_events)

    moisture_series = readings_df["volumetric_water_content"].astype(float)
    current_moisture = _safe_get(moisture_series, -1, 0.0)
    lag_1 = _safe_get(moisture_series, -2, current_moisture)
    lag_2 = _safe_get(moisture_series, -3, lag_1)

    latest_timestamp = readings_df["timestamp"].iloc[-1]
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
        "sensor_count": len(request.soil_moisture_readings),
    }
    return pd.DataFrame([record])
