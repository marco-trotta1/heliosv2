import { PAGE_TITLES, SOIL_THRESHOLDS } from "./constants.js";
import {
  estimateReferenceEtIn,
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

/*
# Solar radiation is not available from NOAA hourly forecasts.
# This monthly climatological estimate is derived from NASA POWER data
# for ~43.6°N (Snake River Plain, Idaho). It is an approximation.
# Replace with measured pyranometer data when available.
*/
const IDAHO_SOLAR_MJ_M2 = {
  1: 7.5,
  2: 10.8,
  3: 15.2,
  4: 19.8,
  5: 23.4,
  6: 26.1,
  7: 26.8,
  8: 23.9,
  9: 18.7,
  10: 12.4,
  11: 7.8,
  12: 6.2,
};

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

function seasonalSolarRadiationEstimate() {
  const month = new Date().getMonth() + 1;
  return IDAHO_SOLAR_MJ_M2[month];
}

function parseWindMph(windSpeed) {
  const matches = String(windSpeed || "").match(/\d+(?:\.\d+)?/g) || [];
  if (matches.length === 0) {
    throw new Error("NOAA forecast is missing a parseable wind speed.");
  }
  const values = matches.map(Number);
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2));
}

export async function fetchNOAAWeather(lat, lon) {
  try {
    const pointsResponse = await fetch(`https://api.weather.gov/points/${lat},${lon}`, {
      headers: {
        Accept: "application/geo+json, application/json",
      },
    });
    if (!pointsResponse.ok) {
      throw new Error(`NOAA points lookup failed with status ${pointsResponse.status}`);
    }
    const pointsJson = await readJsonResponse(pointsResponse);
    const forecastHourlyUrl = pointsJson.properties?.forecastHourly;
    if (typeof forecastHourlyUrl !== "string" || forecastHourlyUrl.length === 0) {
      throw new Error("NOAA points lookup did not return forecastHourly.");
    }

    const forecastResponse = await fetch(forecastHourlyUrl, {
      headers: {
        Accept: "application/geo+json, application/json",
      },
    });
    if (!forecastResponse.ok) {
      throw new Error(`NOAA hourly forecast failed with status ${forecastResponse.status}`);
    }
    const forecastJson = await readJsonResponse(forecastResponse);
    const period = forecastJson.properties?.periods?.[0];
    if (!period) {
      throw new Error("NOAA hourly forecast did not include any periods.");
    }

    if (period.temperature == null || period.relativeHumidity?.value == null) {
      throw new Error("NOAA hourly forecast is missing temperature or humidity.");
    }

    return {
      temperatureF: Number(period.temperature),
      humidityPct: Number(period.relativeHumidity.value),
      windMph: parseWindMph(period.windSpeed),
      precipitationIn: Number(period.probabilityOfPrecipitation?.value || 0) > 50 ? 0.1 : 0.0,
      solarRadiationMjM2: seasonalSolarRadiationEstimate(),
    };
  } catch (error) {
    console.error("[helios] NOAA weather auto-population failed", error);
    return null;
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

// ── Response mapping ───────────────────────────────────────────────────────────

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

  const payload = {
    farm_id: state.latestRun.inputSnapshot.farmId,
    timestamp: new Date().toISOString(),
    crop_type: state.latestRun.inputSnapshot.cropType,
    soil_texture: state.latestRun.inputSnapshot.soilTexture,
    irrigation_type: state.latestRun.inputSnapshot.irrigationType,
    growth_stage: state.latestRun.inputSnapshot.growthStage,
    recommendation_type: "irrigation",
    recommendation_value: String(state.latestRun.recommendedAmountIn),
    outcome: state.feedbackForm.outcome,
    yield_delta: state.feedbackForm.yieldDelta === "" ? null : Number(state.feedbackForm.yieldDelta),
    notes: state.feedbackForm.notes.trim() || null,
    location_lat: Number(state.latestRun.inputSnapshot.locationLat),
    location_lon: Number(state.latestRun.inputSnapshot.locationLon),
  };

  if (!isLiveApiMode()) {
    const FEEDBACK_QUEUE_KEY = "helios-feedback-queue";
    const queue = JSON.parse(localStorage.getItem(FEEDBACK_QUEUE_KEY) || "[]");
    queue.push({ ...payload, queued_at: new Date().toISOString() });
    localStorage.setItem(FEEDBACK_QUEUE_KEY, JSON.stringify(queue));
    state.feedbackForm.status = "Feedback stored locally and will be sent when the backend is available.";
    state.feedbackForm.error = "";
    state.feedbackForm.open = false;
    renderApp();
    return;
  }

  state.feedbackForm.submitting = true;
  state.feedbackForm.error = "";
  state.feedbackForm.status = "";
  renderApp();

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
