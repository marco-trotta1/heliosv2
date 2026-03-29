from __future__ import annotations

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
from helios.utils.evapotranspiration import estimate_reference_et_mm


class RecommendationService:
    def __init__(
        self,
        *,
        model: MoistureForecastModel,
        model_path: Path,
        metadata_path: Path,
    ) -> None:
        self.model = model
        self.model_path = model_path
        self.metadata_path = metadata_path

    @classmethod
    def from_artifacts(
        cls,
        model_path: Path = Path("artifacts/moisture_model.pkl"),
        metadata_path: Path = Path("artifacts/model_metadata.json"),
    ) -> "RecommendationService":
        model = MoistureForecastModel.load(model_path, metadata_path)
        return cls(model=model, model_path=model_path, metadata_path=metadata_path)

    def predict_recommendation(self, request: PredictionRequest) -> PredictionResponse:
        raw_frame = request_to_feature_frame(request)
        features = build_inference_features(raw_frame)
        predicted = self.model.predict(features)

        thresholds = SOIL_THRESHOLDS.get(request.soil_properties.soil_texture, SOIL_THRESHOLDS["loam"])
        estimated_et = estimate_reference_et_mm(
            temperature_c=request.weather.temperature_c,
            humidity_pct=request.weather.humidity_pct,
            wind_mps=request.weather.wind_mps,
            solar_radiation_mj_m2=request.weather.solar_radiation_mj_m2,
        )
        stress_probability = self._compute_stress_probability(
            predicted_moisture_48h=predicted["moisture_48h"],
            dry_threshold=thresholds["dry"],
            estimated_et=estimated_et,
            precipitation_mm=request.weather.precipitation_mm,
            growth_stage=request.crop.growth_stage,
        )

        plan = generate_irrigation_plan(
            OptimizationInputs(
                predicted_moisture=predicted,
                stress_probability=stress_probability,
                soil_texture=request.soil_properties.soil_texture,
                infiltration_rate_mm_per_hour=request.soil_properties.infiltration_rate_mm_per_hour,
                pump_capacity_mm_per_hour=request.irrigation_system.pump_capacity_mm_per_hour,
                water_rights_schedule=request.irrigation_system.water_rights_schedule,
                energy_price_window=request.irrigation_system.energy_price_window,
                max_irrigation_volume_mm=request.operational.max_irrigation_volume_mm,
                field_area_ha=request.operational.field_area_ha,
                budget_dollars=request.operational.budget_dollars,
                estimated_et_mm=estimated_et,
                recent_precipitation_mm=request.weather.precipitation_mm,
                model_rmse=float(self.model.metadata.get("cv_rmse_mean", 0.12)),
                sensor_count=len(request.soil_moisture_readings),
            )
        )

        drivers = self._build_drivers(
            request=request,
            predicted=predicted,
            stress_probability=stress_probability,
            estimated_et=estimated_et,
        )
        response = PredictionResponse(
            decision=plan["decision"],
            recommended_amount_mm=plan["recommended_amount_mm"],
            timing_window=plan["timing_window"],
            confidence_score=plan["confidence_score"],
            explanation=RecommendationExplanation(
                predicted_moisture_48h=predicted["moisture_48h"],
                stress_probability=stress_probability,
                drivers=drivers,
            ),
            predicted_moisture=MoistureForecast(**predicted),
        )
        insights_data = get_regional_insights(
            lat=request.location_lat,
            lon=request.location_lon,
            crop_type=request.crop.crop_type,
            recommendation_type="irrigation",
            soil_texture=request.soil_properties.soil_texture,
            irrigation_type=request.irrigation_system.irrigation_type,
            growth_stage=request.crop.growth_stage,
            season_month=request.soil_moisture_readings[-1].timestamp.month,
        )
        adjustment_data = adjust_recommendation(plan["recommended_amount_mm"], insights_data)
        response.recommended_amount_mm = adjustment_data["adjusted_recommendation_mm"]
        response.regional_insights = RegionalInsights(**insights_data)
        response.recommendation_adjustment = RecommendationAdjustment(
            base_recommendation_mm=plan["recommended_amount_mm"],
            adjusted_recommendation_mm=adjustment_data["adjusted_recommendation_mm"],
            adjustment_factor=adjustment_data["adjustment_factor"],
            reason=adjustment_data["reason"],
        )
        return response

    def _compute_stress_probability(
        self,
        predicted_moisture_48h: float,
        dry_threshold: float,
        estimated_et: float,
        precipitation_mm: float,
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
        score = (moisture_gap * 18.0) + (estimated_et * 0.12) - (precipitation_mm * 0.08) + stage_modifier
        probability = 1.0 / (1.0 + math.exp(-score))
        return round(min(0.99, max(0.01, probability)), 3)

    def _build_drivers(
        self,
        request: PredictionRequest,
        predicted: dict[str, float],
        stress_probability: float,
        estimated_et: float,
    ) -> list[str]:
        drivers: list[str] = []
        current_moisture = request.soil_moisture_readings[-1].volumetric_water_content
        if estimated_et >= 5.5:
            drivers.append("high evapotranspiration")
        if current_moisture <= SOIL_THRESHOLDS[request.soil_properties.soil_texture]["dry"] + 0.04:
            drivers.append("low soil moisture")
        if request.weather.precipitation_mm < 1.5:
            drivers.append("limited forecast precipitation")
        if len(request.irrigation_system.water_rights_schedule) <= 1:
            drivers.append("restrictive water rights window")
        if request.crop.growth_stage in {"flowering", "grain_fill"}:
            drivers.append("sensitive crop growth stage")
        if stress_probability > 0.8 and predicted["moisture_72h"] < predicted["moisture_24h"]:
            drivers.append("continued drying trend")
        return drivers[:3] or ["stable near-threshold moisture"]
