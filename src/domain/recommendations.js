import {
  SOIL_THRESHOLDS,
  ROOT_ZONE_FACTORS,
  IRRIGATION_EFFICIENCY,
  GROWTH_STAGE_MODIFIER,
  TEXTURE_RETENTION,
  DRAINAGE_FACTOR,
} from "../constants.js";
import { clip, formatWindow, round } from "./format.js";

export function estimateReferenceEtIn({ temperatureF, humidityPct, windMph, solarRadiationMjM2, elevationM = 800.0 }) {
  // Simplified FAO-56 Penman-Monteith reference ET0 (in/day)
  const temperatureC = (temperatureF - 32.0) * 5.0 / 9.0;
  const windMps = windMph / 2.23694;
  const atmosphericPressure = 101.3 * Math.pow((293.0 - 0.0065 * elevationM) / 293.0, 5.26);
  const gamma = 0.000665 * atmosphericPressure;
  const eSat = 0.6108 * Math.exp((17.27 * temperatureC) / (temperatureC + 237.3));
  const eAct = eSat * (humidityPct / 100.0);
  const vpd = Math.max(0.0, eSat - eAct);
  const delta = (4098.0 * eSat) / Math.pow(temperatureC + 237.3, 2);
  const rn = 0.77 * solarRadiationMjM2;
  const numerator = (0.408 * delta * rn) + (gamma * (900.0 / (temperatureC + 273.0)) * windMps * vpd);
  const denominator = delta + gamma * (1.0 + 0.34 * windMps);
  const et0Mm = denominator > 0 ? numerator / denominator : 0.0;
  const et0In = Math.max(0.0, et0Mm) * 0.039370;
  return round(et0In, 4);
}

export function predictMoistureTrajectory(inputs, etIn) {
  const retention = TEXTURE_RETENTION[inputs.soilTexture] ?? 1;
  const drainage = DRAINAGE_FACTOR[inputs.drainageClass] ?? 1;
  const irrigationEfficiency = IRRIGATION_EFFICIENCY[inputs.irrigationType] ?? 0.82;
  const trendOne = inputs.currentMoisture - inputs.lagOneMoisture;
  const trendTwo = inputs.lagOneMoisture - inputs.lagTwoMoisture;
  const trendMomentum = trendOne * 0.55 + trendTwo * 0.25;
  const stageLoad = (GROWTH_STAGE_MODIFIER[inputs.growthStage] ?? 0.1) * 0.05;
  const drynessPulse =
    etIn * 0.13208 +
    Math.max(0, inputs.temperatureF - 86) * 0.000722 +
    inputs.windMph * 0.000402 +
    inputs.slopePct * 0.0011 +
    stageLoad;
  const recharge =
    inputs.precipitationIn * 0.08128 +
    inputs.recentIrrigation24h * irrigationEfficiency * 0.06096 +
    inputs.recentIrrigation72h * irrigationEfficiency * 0.02286;
  const effectiveDrying = (drynessPulse * drainage) / retention;
  const resilience = (inputs.infiltrationRate / 24) * 0.015240;

  return {
    moisture24h: round(
      clip(inputs.currentMoisture + trendMomentum * 0.4 + recharge * 0.9 + resilience - effectiveDrying, 0.05, 0.52),
      3,
    ),
    moisture48h: round(
      clip(inputs.currentMoisture + trendMomentum * 0.52 + recharge * 1.22 + resilience * 1.4 - effectiveDrying * 1.84, 0.05, 0.52),
      3,
    ),
    moisture72h: round(
      clip(inputs.currentMoisture + trendMomentum * 0.64 + recharge * 1.36 + resilience * 1.8 - effectiveDrying * 2.6, 0.05, 0.52),
      3,
    ),
  };
}

export function computeStressProbability({ predictedMoisture48h, dryThreshold, estimatedEtIn, precipitationIn, growthStage }) {
  const stageModifier = GROWTH_STAGE_MODIFIER[growthStage] ?? 0.1;
  const moistureGap = dryThreshold - predictedMoisture48h;
  const score = moistureGap * 18 + estimatedEtIn * 3.048 - precipitationIn * 2.032 + stageModifier;
  return round(clip(1 / (1 + Math.exp(-score)), 0.01, 0.99), 3);
}

export function computeBudgetCap(fieldAreaAcres, budgetDollars) {
  if (fieldAreaAcres <= 0) {
    return 0;
  }
  const BUDGET_CONSTANT = 82.25;
  return budgetDollars / (BUDGET_CONSTANT * fieldAreaAcres);
}

export function allowedHours(waterWindows) {
  return Math.max(1, Math.min(12, waterWindows.length * 3));
}

export function selectTimingWindow(waterWindows, energyWindows, needsWater) {
  if (!needsWater) {
    return "monitor next forecast cycle";
  }
  const overlap = waterWindows.find((window) => energyWindows.includes(window));
  if (overlap) {
    return overlap;
  }
  if (waterWindows.length > 0) {
    return waterWindows[0];
  }
  return "next available permitted window";
}

export function scoreConfidence({ forecast48h, dryThreshold, timingWindow, modelRmse = 0.12, sensorCount = 1, precipitationIn = 0 }) {
  const base = Math.max(0.1, 1 - Math.min(modelRmse, 0.50) / 0.50);
  const thresholdMargin = Math.abs(forecast48h - dryThreshold);
  const marginBonus = Math.min(0.2, thresholdMargin / 0.30);
  const sensorPenalty = Math.max(0, 0.12 - sensorCount * 0.03);
  const precipPenalty = Math.min(0.10, precipitationIn * 0.20);
  const timingPenalty = timingWindow === "next available permitted window" ? 0.05 : 0;
  return round(clip(base + marginBonus - sensorPenalty - precipPenalty - timingPenalty, 0.05, 0.99), 3);
}

export function generateIrrigationPlan(inputs, predicted, stressProbability, estimatedEtIn) {
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  const predicted48h = predicted.moisture48h;
  const needsWater = predicted48h < thresholds.dry;
  const timingWindow = selectTimingWindow(inputs.waterWindow, inputs.energyWindow, needsWater);
  const targetMoisture = Math.min(thresholds.wet, thresholds.dry + 0.08 + estimatedEtIn * 0.0508);
  const deficit = Math.max(0, targetMoisture - predicted48h);
  const rawAmountIn = Math.max(
    0,
    deficit * (ROOT_ZONE_FACTORS[inputs.soilTexture] ?? ROOT_ZONE_FACTORS.loam) - inputs.precipitationIn * 0.7,
  );
  const efficiency = IRRIGATION_EFFICIENCY[inputs.irrigationType] || 0.82;
  const grossAmountNeeded = rawAmountIn / efficiency;
  const windowHours = allowedHours(inputs.waterWindow);
  const constraints = {
    need: grossAmountNeeded,
    maxVolume: inputs.maxIrrigationVolume,
    pumpCapacity: inputs.pumpCapacity * windowHours,
    budget: computeBudgetCap(inputs.fieldAreaAcres, inputs.budgetDollars),
    infiltration: inputs.infiltrationRate * windowHours,
  };
  const recommendedAmountIn = Math.min(
    constraints.need,
    constraints.maxVolume,
    constraints.pumpCapacity,
    constraints.budget,
    constraints.infiltration,
  );
  const bindingConstraint = Object.entries(constraints).reduce((min, curr) => curr[1] < min[1] ? curr : min)[0];
  const gaps = Object.fromEntries(Object.entries(constraints).map(([key, value]) => [key, round(value - recommendedAmountIn, 3)]));

  return {
    decision: needsWater ? "water" : "wait",
    recommendedAmountIn: round(needsWater ? recommendedAmountIn : 0, 2),
    timingWindow,
    confidenceScore: scoreConfidence({
      forecast48h: predicted48h,
      dryThreshold: thresholds.dry,
      timingWindow,
      modelRmse: inputs.modelRmse,
      sensorCount: inputs.sensorCount,
      precipitationIn: inputs.precipitationIn,
    }),
    stressProbability,
    thresholds,
    bindingConstraint,
    constraints,
    gaps,
  };
}

export function buildDrivers(inputs, predicted, stressProbability, estimatedEtIn) {
  const drivers = [];
  if (estimatedEtIn >= 0.217) {
    drivers.push("High evapotranspiration is pulling moisture down quickly.");
  }
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  if (inputs.currentMoisture <= thresholds.dry + 0.04) {
    drivers.push("Current soil moisture is already near the crop stress band.");
  }
  if (inputs.precipitationIn < 0.059) {
    drivers.push("Very little forecast rain is expected to refill the root zone.");
  }
  if (inputs.waterWindow.length <= 1) {
    drivers.push("The field has a narrow irrigation availability window.");
  }
  if (["flowering", "grain_fill"].includes(inputs.growthStage)) {
    drivers.push("The crop is in a yield-sensitive growth stage.");
  }
  if (stressProbability > 0.8 && predicted.moisture72h < predicted.moisture24h) {
    drivers.push("The full 72-hour trend keeps moving drier.");
  }
  return drivers.slice(0, 3).length > 0
    ? drivers.slice(0, 3)
    : ["Conditions are stable enough to keep watching instead of watering now."];
}

export function buildSummary(inputs, predicted, plan) {
  const action =
    plan.decision === "water"
      ? `Apply ${plan.recommendedAmountIn.toFixed(2)} in during ${formatWindow(plan.timingWindow)}.`
      : "Hold irrigation and reassess after the next weather update.";
  return `${inputs.fieldName} is forecast to move from ${inputs.currentMoisture.toFixed(2)} now to ${predicted.moisture48h.toFixed(2)} in 48 hours. ${action}`;
}
