import { PAGE_TITLES, SOIL_THRESHOLDS } from "./constants.js";
import {
  estimateReferenceEtMm,
  predictMoistureTrajectory,
  computeStressProbability,
  generateIrrigationPlan,
  buildDrivers,
  buildSummary,
  serializeRunForCopy,
  formatWindow,
} from "./domain.js";
import { state, runtimeConfig, isLiveApiMode, storeRun, persistState } from "./state.js";
// renderApp imported lazily to break circular dep with ui.js
import { renderApp } from "./ui.js";

// ── API helpers ────────────────────────────────────────────────────────────────

export function apiUrl(path) {
  return runtimeConfig.apiBaseUrl ? `${runtimeConfig.apiBaseUrl}${path}` : path;
}

export async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

// ── Request builder ────────────────────────────────────────────────────────────

export function buildPredictionRequest(inputs) {
  const now = new Date();
  const fieldId = inputs.farmId || inputs.fieldName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return {
    field_id: fieldId,
    farm_id: inputs.farmId || fieldId,
    forecast_horizon_hours: 72,
    weather: {
      temperature_c: Number(inputs.temperatureC),
      humidity_pct: Number(inputs.humidityPct),
      wind_mps: Number(inputs.windMps),
      precipitation_mm: Number(inputs.precipitationMm),
      solar_radiation_mj_m2: Number(inputs.solarRadiationMjM2),
      forecast_horizon_hours: 72,
    },
    irrigation_system: {
      irrigation_type: inputs.irrigationType,
      pump_capacity_mm_per_hour: Number(inputs.pumpCapacity),
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
      infiltration_rate_mm_per_hour: Number(inputs.infiltrationRate),
      slope_pct: Number(inputs.slopePct),
      drainage_class: inputs.drainageClass,
    },
    crop: {
      crop_type: inputs.cropType,
      growth_stage: inputs.growthStage,
    },
    operational: {
      max_irrigation_volume_mm: Number(inputs.maxIrrigationVolume),
      field_area_ha: Number(inputs.fieldAreaHa),
      budget_dollars: Number(inputs.budgetDollars),
    },
    location_lat: Number(inputs.locationLat),
    location_lon: Number(inputs.locationLon),
    recent_irrigation_events: [
      {
        timestamp: new Date(now.getTime() - (24 * 60 * 60 * 1000)).toISOString(),
        applied_mm: Number(inputs.recentIrrigation24h),
      },
      {
        timestamp: new Date(now.getTime() - (72 * 60 * 60 * 1000)).toISOString(),
        applied_mm: Number(inputs.recentIrrigation72h),
      },
    ],
  };
}

// ── Response mapping ───────────────────────────────────────────────────────────

function buildApiSummary(inputs, response) {
  const action =
    response.decision === "water"
      ? `Apply ${response.recommended_amount_mm.toFixed(1)} mm during ${formatWindow(response.timing_window)}.`
      : "Hold irrigation and check again after the next weather update.";
  if (response.regional_insights?.total_samples) {
    return `${inputs.fieldName} is being compared with ${response.regional_insights.total_samples} comparable nearby feedback reports. ${action}`;
  }
  return `${inputs.fieldName} has no nearby feedback history yet. ${action}`;
}

export function mapApiRun(inputs, response) {
  const estimatedEtMm = estimateReferenceEtMm(inputs);
  const run = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `${inputs.fieldName} • ${PAGE_TITLES["run-analysis"]}`,
    timestamp: new Date().toISOString(),
    prompt: inputs.analysisPrompt,
    decision: response.decision,
    recommendedAmountMm: Number(response.recommended_amount_mm || 0),
    timingWindow: response.timing_window,
    confidenceScore: Number(response.confidence_score || 0),
    stressProbability: Number(response.explanation?.stress_probability || 0),
    estimatedEtMm,
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
          radiusKm: Number(response.regional_insights.radius_km || 50),
        }
      : null,
    recommendationAdjustment: response.recommendation_adjustment
      ? {
          baseRecommendationMm: Number(response.recommendation_adjustment.base_recommendation_mm || response.recommended_amount_mm || 0),
          adjustedRecommendationMm: Number(response.recommendation_adjustment.adjusted_recommendation_mm || response.recommended_amount_mm || 0),
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
  const estimatedEtMm = estimateReferenceEtMm(inputs);
  const predicted = predictMoistureTrajectory(inputs, estimatedEtMm);
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  const stressProbability = computeStressProbability({
    predictedMoisture48h: predicted.moisture48h,
    dryThreshold: thresholds.dry,
    estimatedEtMm,
    precipitationMm: inputs.precipitationMm,
    growthStage: inputs.growthStage,
  });
  const plan = generateIrrigationPlan(inputs, predicted, stressProbability, estimatedEtMm);
  const drivers = buildDrivers(inputs, predicted, stressProbability, estimatedEtMm);
  const run = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `${inputs.fieldName} • ${PAGE_TITLES["run-analysis"]}`,
    timestamp: new Date().toISOString(),
    prompt: inputs.analysisPrompt,
    decision: plan.decision,
    recommendedAmountMm: plan.recommendedAmountMm,
    timingWindow: plan.timingWindow,
    confidenceScore: plan.confidenceScore,
    stressProbability: plan.stressProbability,
    estimatedEtMm,
    predicted,
    drivers,
    summary: buildSummary(inputs, predicted, plan),
    inputSnapshot: inputs,
    regionalInsights: null,
    recommendationAdjustment: {
      baseRecommendationMm: plan.recommendedAmountMm,
      adjustedRecommendationMm: plan.recommendedAmountMm,
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

// ── Regional insights ──────────────────────────────────────────────────────────

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
    radius: "50",
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
    radiusKm: Number(result.radius_km || 50),
  };
  run.copyText = serializeRunForCopy(run);
}

// ── Scenario evaluation ────────────────────────────────────────────────────────

export async function evaluateScenario() {
  const inputs = { ...state.form };
  if (state.analysis.submitting) {
    return;
  }
  state.analysis.submitting = true;
  state.analysis.error = "";
  state.analysis.status = isLiveApiMode()
    ? "Running recommendation with nearby feedback..."
    : "Running local demo estimate. No live backend call will be made.";
  renderApp();

  if (!isLiveApiMode()) {
    const run = buildLocalRun(inputs);
    storeRun(run);
    state.analysis.source = "demo";
    state.analysis.status = runtimeConfig.disclaimer;
    state.analysis.submitting = false;
    renderApp();
    return;
  }

  try {
    const response = await fetch(apiUrl("/predict"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildPredictionRequest(inputs)),
    });
    const result = await readJsonResponse(response);
    if (!response.ok) {
      throw new Error(result.detail || "Unable to run the recommendation service.");
    }
    const run = mapApiRun(inputs, result);
    storeRun(run);
    state.analysis.source = "api";
    state.analysis.status = run.regionalInsights?.totalSamples
      ? `Recommendation updated using ${run.regionalInsights.totalSamples} nearby feedback reports.`
      : "Recommendation completed. No nearby feedback reports were available yet.";
  } catch (error) {
    const run = buildLocalRun(inputs);
    storeRun(run);
    state.analysis.source = "local";
    state.analysis.error = error instanceof Error ? error.message : "Unable to reach the recommendation service.";
    state.analysis.status = "Showing the local demo estimate because the live API could not be reached.";
  } finally {
    state.analysis.submitting = false;
    renderApp();
  }
}

// ── Feedback submission ────────────────────────────────────────────────────────

export async function submitFeedback() {
  if (!state.latestRun || state.feedbackForm.submitting) {
    return;
  }

  if (!isLiveApiMode()) {
    state.feedbackForm.status = "Live API mode is required to store feedback in the Helios database.";
    state.feedbackForm.error = "";
    state.feedbackForm.open = false;
    renderApp();
    return;
  }

  state.feedbackForm.submitting = true;
  state.feedbackForm.error = "";
  state.feedbackForm.status = "";
  renderApp();

  const payload = {
    farm_id: state.latestRun.inputSnapshot.farmId,
    timestamp: new Date().toISOString(),
    crop_type: state.latestRun.inputSnapshot.cropType,
    soil_texture: state.latestRun.inputSnapshot.soilTexture,
    irrigation_type: state.latestRun.inputSnapshot.irrigationType,
    growth_stage: state.latestRun.inputSnapshot.growthStage,
    recommendation_type: "irrigation",
    recommendation_value: String(state.latestRun.recommendedAmountMm),
    outcome: state.feedbackForm.outcome,
    yield_delta: state.feedbackForm.yieldDelta === "" ? null : Number(state.feedbackForm.yieldDelta),
    notes: state.feedbackForm.notes.trim() || null,
    location_lat: Number(state.latestRun.inputSnapshot.locationLat),
    location_lon: Number(state.latestRun.inputSnapshot.locationLon),
  };

  try {
    const response = await fetch(apiUrl("/api/feedback"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const result = await readJsonResponse(response);
    if (!response.ok) {
      throw new Error(result.detail || "Unable to submit feedback.");
    }
    state.feedbackForm.status = result.message || "Feedback recorded.";
    state.feedbackForm.error = "";
    state.feedbackForm.open = false;
    state.feedbackForm.yieldDelta = "";
    state.feedbackForm.notes = "";
    try {
      await refreshRegionalInsights(state.latestRun);
      persistState();
    } catch {
      // Keep the successful feedback confirmation even if the summary refresh fails.
    }
  } catch (error) {
    state.feedbackForm.error = error instanceof Error ? error.message : "Unable to submit feedback.";
  } finally {
    state.feedbackForm.submitting = false;
    renderApp();
  }
}
