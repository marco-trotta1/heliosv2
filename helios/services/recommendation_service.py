from __future__ import annotations

import logging
import math
from pathlib import Path

from helios.data.feature_engineering import build_inference_features
from helios.data.ingestion import request_to_feature_frame
from helios.lib.feedback import adjust_recommendation, get_regional_insights
from helios.models.moisture_model import MoistureForecastModel
from helios.optimizer.irrigation_optimizer import OptimizationInputs, SOIL_THRESHOLDS, generate_irrigation_plan
from helios.schemas.inputs import PredictionRequest
from helios.schemas.outputs import (
    MoistureForecast,
    PredictionResponse,
    RecommendationAdjustment,
    RecommendationExplanation,
    RegionalInsights,
)
from helios.utils.evapotranspiration import estimate_reference_et_in
from helios.utils.openet import resolve_monthly_et_in


logger = logging.getLogger(__name__)

VALIDATION_REGIONAL_INSIGHTS = {
    "success_rate": 0.0,
    "avg_yield_delta": None,
    "total_samples": 0,
    "weighted_samples": 0.0,
    "comparable_samples": 0,
    "radius_miles": 31.07,
}
VALIDATION_ADJUSTMENT_REASON = (
    "Validation mode is enabled, so nearby feedback adjustments were disabled for a clean field test."
)


class RecommendationService:
    def __init__(
        self,
        *,
        model: MoistureForecastModel,
        model_path: Path,
        metadata_path: Path,
        validation_mode: bool = False,
    ) -> None:
        self.model = model
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.validation_mode = validation_mode

    @classmethod
    def from_artifacts(
        cls,
        model_path: Path = Path("artifacts/moisture_model.pkl"),
        metadata_path: Path = Path("artifacts/model_metadata.json"),
        validation_mode: bool = False,
    ) -> "RecommendationService":
        model = MoistureForecastModel.load(model_path, metadata_path)
        return cls(
            model=model,
            model_path=model_path,
            metadata_path=metadata_path,
            validation_mode=validation_mode,
        )

    def predict_recommendation(self, request: PredictionRequest) -> PredictionResponse:
        latest_timestamp = max(reading.timestamp for reading in request.soil_moisture_readings)
        openet_monthly_et_in, openet_source = resolve_monthly_et_in(
            longitude=request.location_lon,
            latitude=request.location_lat,
            observed_at=latest_timestamp,
        )
        logger.info(
            "prediction openet source selected",
            extra={
                "field_id": request.field_id,
                "openet_source": openet_source,
            },
        )

        raw_frame = request_to_feature_frame(request, openet_monthly_et_in=openet_monthly_et_in)
        primary_sensor_id = str(raw_frame.iloc[0]["primary_sensor_id"])
        physical_sensor_count = int(raw_frame.iloc[0]["physical_sensor_count"])
        zone_moisture_summary = self._latest_zone_moisture_summary(request)
        moisture_spread = max(zone_moisture_summary.values()) - min(zone_moisture_summary.values())
        high_variability_flag = moisture_spread > 0.12
        features = build_inference_features(raw_frame)
        predicted = self.model.predict(features)

        thresholds = SOIL_THRESHOLDS.get(request.soil_properties.soil_texture, SOIL_THRESHOLDS["loam"])
        estimated_et = estimate_reference_et_in(
            temperature_f=request.weather.temperature_f,
            humidity_pct=request.weather.humidity_pct,
            wind_mph=request.weather.wind_mph,
            solar_radiation_mj_m2=request.weather.solar_radiation_mj_m2,
        )
        stress_probability = self._compute_stress_probability(
            predicted_moisture_48h=predicted["moisture_48h"],
            dry_threshold=thresholds["dry"],
            estimated_et=estimated_et,
            precipitation_in=request.weather.precipitation_in,
            growth_stage=request.crop.growth_stage,
        )

        plan = generate_irrigation_plan(
            OptimizationInputs(
                predicted_moisture=predicted,
                stress_probability=stress_probability,
                soil_texture=request.soil_properties.soil_texture,
                infiltration_rate_in_per_hour=request.soil_properties.infiltration_rate_in_per_hour,
                pump_capacity_in_per_hour=request.irrigation_system.pump_capacity_in_per_hour,
                water_rights_schedule=request.irrigation_system.water_rights_schedule,
                energy_price_window=request.irrigation_system.energy_price_window,
                max_irrigation_volume_in=request.operational.max_irrigation_volume_in,
                field_area_acres=request.operational.field_area_acres,
                budget_dollars=request.operational.budget_dollars,
                estimated_et_in=estimated_et,
                recent_precipitation_in=request.weather.precipitation_in,
                model_rmse=float(self.model.metadata.get("cv_rmse_mean", 0.12)),
                sensor_count=len(request.soil_moisture_readings),
                physical_sensor_count=physical_sensor_count,
            )
        )

        drivers = self._build_drivers(
            request=request,
            predicted=predicted,
            stress_probability=stress_probability,
            estimated_et=estimated_et,
            current_moisture=float(raw_frame.iloc[0]["current_soil_moisture"]),
        )
        if self.validation_mode:
            insights_data = dict(VALIDATION_REGIONAL_INSIGHTS)
            adjustment_data = {
                "adjusted_recommendation_in": round(plan["recommended_amount_in"], 2),
                "adjustment_factor": 1.0,
                "reason": VALIDATION_ADJUSTMENT_REASON,
            }
        else:
            insights_data = get_regional_insights(
                lat=request.location_lat,
                lon=request.location_lon,
                crop_type=request.crop.crop_type,
                recommendation_type="irrigation",
                soil_texture=request.soil_properties.soil_texture,
                irrigation_type=request.irrigation_system.irrigation_type,
                growth_stage=request.crop.growth_stage,
                season_month=latest_timestamp.month,
            )
            adjustment_data = adjust_recommendation(plan["recommended_amount_in"], insights_data)

        response = PredictionResponse(
            decision=plan["decision"],
            recommended_amount_in=adjustment_data["adjusted_recommendation_in"],
            timing_window=plan["timing_window"],
            confidence_score=plan["confidence_score"],
            et_source=openet_source,
            explanation=RecommendationExplanation(
                predicted_moisture_48h=predicted["moisture_48h"],
                stress_probability=stress_probability,
                drivers=drivers,
                driving_zone=primary_sensor_id,
                zone_moisture_summary=zone_moisture_summary,
                high_variability_flag=high_variability_flag,
            ),
            predicted_moisture=MoistureForecast(**predicted),
            regional_insights=RegionalInsights(**insights_data),
            recommendation_adjustment=RecommendationAdjustment(
                base_recommendation_in=plan["recommended_amount_in"],
                adjusted_recommendation_in=adjustment_data["adjusted_recommendation_in"],
                adjustment_factor=adjustment_data["adjustment_factor"],
                reason=adjustment_data["reason"],
            ),
        )
        return response

    def _compute_stress_probability(
        self,
        predicted_moisture_48h: float,
        dry_threshold: float,
        estimated_et: float,
        precipitation_in: float,
        growth_stage: str,
    ) -> float:
        stage_modifier = {
            "emergence": 0.05,
            "vegetative": 0.1,
            "flowering": 0.18,
            "grain_fill": 0.14,
            "maturity": 0.02,
        }.get(growth_stage, 0.1)
        moisture_gap = dry_threshold - predicted_moisture_48h
        # ET is in in/day; precipitation is in inches — scale coefficients accordingly
        score = (moisture_gap * 18.0) + (estimated_et * 3.048) - (precipitation_in * 2.032) + stage_modifier
        probability = 1.0 / (1.0 + math.exp(-score))
        return round(min(0.99, max(0.01, probability)), 3)

    def _build_drivers(
        self,
        request: PredictionRequest,
        predicted: dict[str, float],
        stress_probability: float,
        estimated_et: float,
        current_moisture: float,
    ) -> list[str]:
        drivers: list[str] = []
        if estimated_et >= 0.217:  # ~5.5 mm/day in inches
            drivers.append("high evapotranspiration")
        if current_moisture <= SOIL_THRESHOLDS[request.soil_properties.soil_texture]["dry"] + 0.04:
            drivers.append("low soil moisture")
        if request.weather.precipitation_in < 0.059:  # ~1.5 mm in inches
            drivers.append("limited forecast precipitation")
        if len(request.irrigation_system.water_rights_schedule) <= 1:
            drivers.append("restrictive water rights window")
        if request.crop.growth_stage in {"flowering", "grain_fill"}:
            drivers.append("sensitive crop growth stage")
        if stress_probability > 0.8 and predicted["moisture_72h"] < predicted["moisture_24h"]:
            drivers.append("continued drying trend")
        return drivers[:3] or ["stable near-threshold moisture"]

    def _latest_zone_moisture_summary(self, request: PredictionRequest) -> dict[str, float]:
        latest_by_sensor: dict[str, tuple[object, float]] = {}
        for reading in request.soil_moisture_readings:
            existing = latest_by_sensor.get(reading.sensor_id)
            if existing is None or reading.timestamp > existing[0]:
                latest_by_sensor[reading.sensor_id] = (
                    reading.timestamp,
                    reading.volumetric_water_content,
                )
        return {
            sensor_id: float(latest_by_sensor[sensor_id][1])
            for sensor_id in sorted(latest_by_sensor)
        }
