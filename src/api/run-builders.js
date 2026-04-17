import { PAGE_TITLES, SOIL_THRESHOLDS } from "../constants.js";
import {
  estimateReferenceEtIn,
  predictMoistureTrajectory,
  computeStressProbability,
  generateIrrigationPlan,
  buildDrivers,
  buildSummary,
  serializeRunForCopy,
  formatWindow,
} from "../domain.js";
import { isLiveApiMode } from "../state.js";
import { apiUrl, readJsonResponse } from "./http.js";

export function buildPredictionRequest(inputs) {
  const now = new Date();
  const fieldId = inputs.farmId || inputs.fieldName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return {
    field_id: fieldId,
    farm_id: inputs.farmId || fieldId,
    forecast_horizon_hours: 72,
    weather: {
      temperature_f: Number(inputs.temperatureF),
      humidity_pct: Number(inputs.humidityPct),
      wind_mph: Number(inputs.windMph),
      precipitation_in: Number(inputs.precipitationIn),
      solar_radiation_mj_m2: Number(inputs.solarRadiationMjM2),
      forecast_horizon_hours: 72,
    },
    irrigation_system: {
      irrigation_type: inputs.irrigationType,
      pump_capacity_in_per_hour: Number(inputs.pumpCapacity),
      water_rights_schedule: inputs.waterWindow,
      energy_price_window: inputs.energyWindow,
    },
    soil_moisture_readings: [
      {
        timestamp: new Date(now.getTime() - (12 * 60 * 60 * 1000)).toISOString(),
        field_id: fieldId,
        volumetric_water_content: Number(inputs.lagTwoMoisture),
      },
      {
        timestamp: new Date(now.getTime() - (6 * 60 * 60 * 1000)).toISOString(),
        field_id: fieldId,
        volumetric_water_content: Number(inputs.lagOneMoisture),
      },
      {
        timestamp: now.toISOString(),
        field_id: fieldId,
        volumetric_water_content: Number(inputs.currentMoisture),
      },
    ],
    soil_properties: {
      soil_texture: inputs.soilTexture,
      infiltration_rate_in_per_hour: Number(inputs.infiltrationRate),
      slope_pct: Number(inputs.slopePct),
      drainage_class: inputs.drainageClass,
    },
    crop: {
      crop_type: inputs.cropType,
      growth_stage: inputs.growthStage,
    },
    operational: {
      max_irrigation_volume_in: Number(inputs.maxIrrigationVolume),
      field_area_acres: Number(inputs.fieldAreaAcres),
      budget_dollars: Number(inputs.budgetDollars),
    },
    location_lat: Number(inputs.locationLat),
    location_lon: Number(inputs.locationLon),
    recent_irrigation_events: [
      {
        timestamp: new Date(now.getTime() - (24 * 60 * 60 * 1000)).toISOString(),
        applied_in: Number(inputs.recentIrrigation24h),
      },
      {
        timestamp: new Date(now.getTime() - (72 * 60 * 60 * 1000)).toISOString(),
        applied_in: Number(inputs.recentIrrigation72h),
      },
    ],
  };
}

function buildApiSummary(inputs, response) {
  const action =
    response.decision === "water"
      ? `Apply ${Number(response.recommended_amount_in).toFixed(2)} in during ${formatWindow(response.timing_window)}.`
      : "Hold irrigation and check again after the next weather update.";
  if (response.regional_insights?.total_samples) {
    return `${inputs.fieldName} is being compared with ${response.regional_insights.total_samples} comparable nearby feedback reports. ${action}`;
  }
  return `${inputs.fieldName} has no nearby feedback history yet. ${action}`;
}

export function mapApiRun(inputs, response) {
  const estimatedEtIn = estimateReferenceEtIn(inputs);
  const run = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `${inputs.fieldName} • ${PAGE_TITLES["run-analysis"]}`,
    timestamp: new Date().toISOString(),
    prompt: inputs.analysisPrompt,
    decision: response.decision,
    recommendedAmountIn: Number(response.recommended_amount_in || 0),
    timingWindow: response.timing_window,
    confidenceScore: Number(response.confidence_score || 0),
    stressProbability: Number(response.explanation?.stress_probability || 0),
    estimatedEtIn,
    predicted: {
      moisture24h: Number(response.predicted_moisture?.moisture_24h || 0),
      moisture48h: Number(response.predicted_moisture?.moisture_48h || 0),
      moisture72h: Number(response.predicted_moisture?.moisture_72h || 0),
    },
    drivers: Array.isArray(response.explanation?.drivers) ? response.explanation.drivers : [],
    summary: buildApiSummary(inputs, response),
    inputSnapshot: inputs,
    regionalInsights: response.regional_insights
      ? {
          successRate: Number(response.regional_insights.success_rate || 0),
          avgYieldDelta: response.regional_insights.avg_yield_delta,
          totalSamples: Number(response.regional_insights.total_samples || 0),
          weightedSamples: Number(response.regional_insights.weighted_samples || 0),
          radiusMiles: Number(response.regional_insights.radius_miles || 31.07),
        }
      : null,
    recommendationAdjustment: response.recommendation_adjustment
      ? {
          baseRecommendationIn: Number(response.recommendation_adjustment.base_recommendation_in || response.recommended_amount_in || 0),
          adjustedRecommendationIn: Number(response.recommendation_adjustment.adjusted_recommendation_in || response.recommended_amount_in || 0),
          adjustmentFactor: Number(response.recommendation_adjustment.adjustment_factor || 1),
          reason: response.recommendation_adjustment.reason || "No adjustment reason returned.",
        }
      : null,
    sourceLabel: "Live API with nearby farm feedback",
    copyText: "",
  };
  run.copyText = serializeRunForCopy(run);
  return run;
}

export function buildLocalRun(inputs) {
  const estimatedEtIn = estimateReferenceEtIn(inputs);
  const predicted = predictMoistureTrajectory(inputs, estimatedEtIn);
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  const stressProbability = computeStressProbability({
    predictedMoisture48h: predicted.moisture48h,
    dryThreshold: thresholds.dry,
    estimatedEtIn,
    precipitationIn: inputs.precipitationIn,
    growthStage: inputs.growthStage,
  });
  const plan = generateIrrigationPlan(inputs, predicted, stressProbability, estimatedEtIn);
  const drivers = buildDrivers(inputs, predicted, stressProbability, estimatedEtIn);
  const run = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `${inputs.fieldName} • ${PAGE_TITLES["run-analysis"]}`,
    timestamp: new Date().toISOString(),
    prompt: inputs.analysisPrompt,
    decision: plan.decision,
    recommendedAmountIn: plan.recommendedAmountIn,
    timingWindow: plan.timingWindow,
    confidenceScore: plan.confidenceScore,
    stressProbability: plan.stressProbability,
    bindingConstraint: plan.bindingConstraint,
    estimatedEtIn,
    predicted,
    drivers,
    summary: buildSummary(inputs, predicted, plan),
    inputSnapshot: inputs,
    regionalInsights: null,
    recommendationAdjustment: {
      baseRecommendationIn: plan.recommendedAmountIn,
      adjustedRecommendationIn: plan.recommendedAmountIn,
      adjustmentFactor: 1,
      reason: isLiveApiMode()
        ? "Live feedback service was unavailable, so this result uses the local prototype rules only."
        : "Demo mode uses the local prototype rules only. No backend model or stored feedback was used.",
    },
    sourceLabel: isLiveApiMode() ? "Local fallback estimate" : "Static demo estimate",
    copyText: "",
  };
  run.copyText = serializeRunForCopy(run);
  return run;
}

export async function refreshRegionalInsights(run) {
  if (!isLiveApiMode()) {
    return;
  }
  if (run?.inputSnapshot?.locationLat == null || run?.inputSnapshot?.locationLon == null) {
    return;
  }
  const params = new URLSearchParams({
    lat: String(run.inputSnapshot.locationLat),
    lon: String(run.inputSnapshot.locationLon),
    radius: "31.07",
    crop_type: run.inputSnapshot.cropType,
    recommendation_type: "irrigation",
    soil_texture: run.inputSnapshot.soilTexture,
    irrigation_type: run.inputSnapshot.irrigationType,
    growth_stage: run.inputSnapshot.growthStage,
    season_month: String(new Date(run.timestamp).getUTCMonth() + 1),
  });
  const response = await fetch(apiUrl(`/api/feedback/nearby?${params.toString()}`));
  const result = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(result.detail || "Unable to refresh nearby feedback.");
  }
  run.regionalInsights = {
    successRate: Number(result.success_rate || 0),
    avgYieldDelta: result.avg_yield_delta,
    totalSamples: Number(result.total_samples || 0),
    weightedSamples: Number(result.weighted_samples || 0),
    radiusMiles: Number(result.radius_miles || 31.07),
  };
  run.copyText = serializeRunForCopy(run);
}
