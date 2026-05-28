from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_HORIZONS = {24, 48, 72}
FUTURE_TIMESTAMP_SKEW = timedelta(minutes=5)
MIN_TEMPERATURE_F = -40.0
MAX_TEMPERATURE_F = 130.0
MAX_WIND_MPH = 80.0
MAX_PRECIPITATION_IN = 12.0
MAX_SOLAR_RADIATION_MJ_M2 = 35.0


def _validate_allowed_horizon(value: int | None) -> int | None:
    if value is None:
        return value
    if value not in ALLOWED_HORIZONS:
        raise ValueError("forecast_horizon_hours must be one of 24, 48, or 72")
    return value


def _validate_sensor_readings(value: list["SoilMoistureReading"]) -> list["SoilMoistureReading"]:
    if not value:
        raise ValueError("at least 1 soil moisture sensor with readings is required")

    grouped: dict[str, int] = {}
    for reading in value:
        sensor_id = reading.sensor_id.strip()
        if not sensor_id:
            raise ValueError("soil moisture readings must include a non-empty sensor_id")
        grouped[sensor_id] = grouped.get(sensor_id, 0) + 1

    if not grouped:
        raise ValueError("at least 1 soil moisture sensor with readings is required")

    violations = [
        f"sensor '{sensor_id}' requires at least 3 soil moisture readings; received {count}"
        for sensor_id, count in sorted(grouped.items())
        if count < 3
    ]
    if violations:
        raise ValueError("; ".join(violations))
    return value


def _validate_prediction_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("prediction timestamps must be timezone-aware")
    timestamp = value.astimezone(timezone.utc)
    if timestamp > datetime.now(timezone.utc) + FUTURE_TIMESTAMP_SKEW:
        raise ValueError("prediction timestamps cannot be in the future")
    return timestamp


class RequiredHorizonModel(BaseModel):
    @field_validator("forecast_horizon_hours", check_fields=False)
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        validated = _validate_allowed_horizon(value)
        assert validated is not None
        return validated


class WeatherInput(RequiredHorizonModel):
    temperature_f: float = Field(ge=MIN_TEMPERATURE_F, le=MAX_TEMPERATURE_F)
    humidity_pct: float = Field(ge=0, le=100)
    wind_mph: float = Field(ge=0, le=MAX_WIND_MPH)
    precipitation_in: float = Field(ge=0, le=MAX_PRECIPITATION_IN)
    solar_radiation_mj_m2: float = Field(ge=0, le=MAX_SOLAR_RADIATION_MJ_M2)
    forecast_horizon_hours: int


class WeatherInputPatch(BaseModel):
    temperature_f: float | None = Field(
        default=None,
        ge=MIN_TEMPERATURE_F,
        le=MAX_TEMPERATURE_F,
    )
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    wind_mph: float | None = Field(default=None, ge=0, le=MAX_WIND_MPH)
    precipitation_in: float | None = Field(default=None, ge=0, le=MAX_PRECIPITATION_IN)
    solar_radiation_mj_m2: float | None = Field(
        default=None,
        ge=0,
        le=MAX_SOLAR_RADIATION_MJ_M2,
    )
    forecast_horizon_hours: int | None = None

    @field_validator("forecast_horizon_hours")
    @classmethod
    def validate_horizon(cls, value: int | None) -> int | None:
        return _validate_allowed_horizon(value)


class IrrigationSystemInput(BaseModel):
    irrigation_type: Literal["pivot", "drip", "flood"]
    pump_capacity_in_per_hour: float = Field(gt=0)
    water_rights_schedule: list[str] = Field(min_length=1)
    energy_price_window: list[str] = Field(default_factory=list)


class SoilMoistureReading(BaseModel):
    timestamp: datetime
    field_id: str
    sensor_id: str
    volumetric_water_content: float = Field(ge=0, le=1)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _validate_prediction_timestamp(value)


class SoilPropertiesInput(BaseModel):
    soil_texture: Literal["sand", "loam", "clay"]
    infiltration_rate_in_per_hour: float = Field(gt=0)
    slope_pct: float = Field(ge=0)
    drainage_class: Literal["poor", "moderate", "well"]


class CropInput(BaseModel):
    crop_type: Literal["corn", "soybean", "alfalfa", "potato"]
    growth_stage: Literal["emergence", "vegetative", "flowering", "grain_fill", "maturity"]


class OperationalConstraintsInput(BaseModel):
    max_irrigation_volume_in: float = Field(ge=0)
    field_area_acres: float = Field(gt=0)
    budget_dollars: float = Field(ge=0)


class IrrigationEventInput(BaseModel):
    timestamp: datetime
    applied_in: float = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _validate_prediction_timestamp(value)


class PredictionRequest(RequiredHorizonModel):
    field_id: str = Field(min_length=1)
    farm_id: str | None = Field(default=None, min_length=1)
    forecast_horizon_hours: int
    weather: WeatherInput
    irrigation_system: IrrigationSystemInput
    soil_moisture_readings: list[SoilMoistureReading]
    soil_properties: SoilPropertiesInput
    crop: CropInput
    operational: OperationalConstraintsInput
    location_lat: float = Field(ge=-90, le=90)
    location_lon: float = Field(ge=-180, le=180)
    recent_irrigation_events: list[IrrigationEventInput] = Field(default_factory=list)

    @field_validator("soil_moisture_readings")
    @classmethod
    def validate_readings(cls, value: list[SoilMoistureReading]) -> list[SoilMoistureReading]:
        return _validate_sensor_readings(value)

    @model_validator(mode="after")
    def validate_consistency(self) -> "PredictionRequest":
        if self.weather.forecast_horizon_hours != self.forecast_horizon_hours:
            raise ValueError("weather.forecast_horizon_hours must match forecast_horizon_hours")
        field_ids = {reading.field_id for reading in self.soil_moisture_readings}
        if field_ids != {self.field_id}:
            raise ValueError("all soil moisture readings must match field_id")
        if self.farm_id is None:
            self.farm_id = self.field_id
        return self


class PredictionRequestPayload(RequiredHorizonModel):
    field_id: str = Field(min_length=1)
    farm_id: str | None = Field(default=None, min_length=1)
    forecast_horizon_hours: int
    weather: WeatherInputPatch | None = None
    irrigation_system: IrrigationSystemInput
    soil_moisture_readings: list[SoilMoistureReading]
    soil_properties: SoilPropertiesInput
    crop: CropInput
    operational: OperationalConstraintsInput
    location_lat: float = Field(ge=-90, le=90)
    location_lon: float = Field(ge=-180, le=180)
    recent_irrigation_events: list[IrrigationEventInput] = Field(default_factory=list)

    @field_validator("soil_moisture_readings")
    @classmethod
    def validate_readings(cls, value: list[SoilMoistureReading]) -> list[SoilMoistureReading]:
        return _validate_sensor_readings(value)

    @model_validator(mode="after")
    def validate_consistency(self) -> "PredictionRequestPayload":
        field_ids = {reading.field_id for reading in self.soil_moisture_readings}
        if field_ids != {self.field_id}:
            raise ValueError("all soil moisture readings must match field_id")
        if self.farm_id is None:
            self.farm_id = self.field_id
        return self


class FeedbackCreateRequest(BaseModel):
    farm_id: str = Field(min_length=1)
    timestamp: datetime
    crop_type: str = Field(min_length=1)
    soil_texture: Literal["sand", "loam", "clay"]
    irrigation_type: Literal["pivot", "drip", "flood"]
    growth_stage: Literal["emergence", "vegetative", "flowering", "grain_fill", "maturity"]
    recommendation_type: str = Field(min_length=1)
    recommendation_value: str = Field(min_length=1)
    outcome: Literal["SUCCESS", "PARTIAL", "FAILURE"]
    yield_delta: float | None = None
    notes: str | None = Field(default=None, max_length=2000)
    location_lat: float = Field(ge=-90, le=90)
    location_lon: float = Field(ge=-180, le=180)

    @field_validator("yield_delta")
    @classmethod
    def validate_yield_delta(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < -100 or value > 1000:
            raise ValueError("yield_delta must be between -100 and 1000 percent")
        return value

    @model_validator(mode="after")
    def normalize_feedback(self) -> "FeedbackCreateRequest":
        current_time = datetime.now(timezone.utc)
        timestamp = self.timestamp.astimezone(timezone.utc) if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=timezone.utc)
        if timestamp > current_time:
            raise ValueError("timestamp cannot be in the future")
        if self.notes is not None:
            cleaned = self.notes.strip()
            self.notes = cleaned or None
        return self


class AcknowledgementRequest(BaseModel):
    field_id: str = Field(min_length=1)
    farm_id: str = Field(min_length=1)
    timestamp: datetime
    recommendation_summary: str = Field(max_length=2000)
