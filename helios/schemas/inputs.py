from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_HORIZONS = {24, 48, 72}


class WeatherInput(BaseModel):
    temperature_f: float
    humidity_pct: float = Field(ge=0, le=100)
    wind_mph: float = Field(ge=0)
    precipitation_in: float = Field(ge=0)
    solar_radiation_mj_m2: float = Field(ge=0)
    forecast_horizon_hours: int

    @field_validator("forecast_horizon_hours")
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        if value not in ALLOWED_HORIZONS:
            raise ValueError("forecast_horizon_hours must be one of 24, 48, or 72")
        return value


class WeatherInputPatch(BaseModel):
    temperature_f: float | None = None
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    wind_mph: float | None = Field(default=None, ge=0)
    precipitation_in: float | None = Field(default=None, ge=0)
    solar_radiation_mj_m2: float | None = Field(default=None, ge=0)
    forecast_horizon_hours: int | None = None

    @field_validator("forecast_horizon_hours")
    @classmethod
    def validate_horizon(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in ALLOWED_HORIZONS:
            raise ValueError("forecast_horizon_hours must be one of 24, 48, or 72")
        return value


class IrrigationSystemInput(BaseModel):
    irrigation_type: Literal["pivot", "drip", "flood"]
    pump_capacity_in_per_hour: float = Field(gt=0)
    water_rights_schedule: list[str] = Field(min_length=1)
    energy_price_window: list[str] = Field(default_factory=list)


class SoilMoistureReading(BaseModel):
    timestamp: datetime
    field_id: str
    volumetric_water_content: float = Field(ge=0, le=1)


class SoilPropertiesInput(BaseModel):
    soil_texture: Literal["sand", "loam", "clay"]
    infiltration_rate_in_per_hour: float = Field(gt=0)
    slope_pct: float = Field(ge=0)
    drainage_class: Literal["poor", "moderate", "well"]


class CropInput(BaseModel):
    crop_type: str = Field(min_length=1)
    growth_stage: Literal["emergence", "vegetative", "flowering", "grain_fill", "maturity"]


class OperationalConstraintsInput(BaseModel):
    max_irrigation_volume_in: float = Field(ge=0)
    field_area_acres: float = Field(gt=0)
    budget_dollars: float = Field(ge=0)


class IrrigationEventInput(BaseModel):
    timestamp: datetime
    applied_in: float = Field(ge=0)


class PredictionRequest(BaseModel):
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

    @field_validator("forecast_horizon_hours")
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        if value not in ALLOWED_HORIZONS:
            raise ValueError("forecast_horizon_hours must be one of 24, 48, or 72")
        return value

    @field_validator("soil_moisture_readings")
    @classmethod
    def validate_readings(cls, value: list[SoilMoistureReading]) -> list[SoilMoistureReading]:
        if len(value) < 3:
            raise ValueError("at least 3 soil moisture readings are required")
        return value

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


class PredictionRequestPayload(BaseModel):
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

    @field_validator("forecast_horizon_hours")
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        if value not in ALLOWED_HORIZONS:
            raise ValueError("forecast_horizon_hours must be one of 24, 48, or 72")
        return value

    @field_validator("soil_moisture_readings")
    @classmethod
    def validate_readings(cls, value: list[SoilMoistureReading]) -> list[SoilMoistureReading]:
        if len(value) < 3:
            raise ValueError("at least 3 soil moisture readings are required")
        return value

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


class NearbyFeedbackQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_miles: float = Field(default=31.07, gt=0, le=310.7)
    crop_type: str | None = None
    recommendation_type: str | None = None
    soil_texture: Literal["sand", "loam", "clay"] | None = None
    irrigation_type: Literal["pivot", "drip", "flood"] | None = None
    growth_stage: Literal["emergence", "vegetative", "flowering", "grain_fill", "maturity"] | None = None
