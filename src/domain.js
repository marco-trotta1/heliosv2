import {
  SOIL_THRESHOLDS,
  ROOT_ZONE_FACTORS,
  IRRIGATION_EFFICIENCY,
  GROWTH_STAGE_MODIFIER,
  TEXTURE_RETENTION,
  DRAINAGE_FACTOR,
} from "./constants.js";

// ── Numeric helpers ────────────────────────────────────────────────────────────

export function round(value, decimals = 1) {
  return Number(value.toFixed(decimals));
}

export function clip(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

// ── Formatting helpers ─────────────────────────────────────────────────────────

export function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

export function formatWindow(value) {
  const words = value.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ── ET₀ (FAO-56 Penman-Monteith) ──────────────────────────────────────────────

export function estimateReferenceEtIn({ temperatureF, humidityPct, windMph, solarRadiationMjM2, elevationM = 800.0 }) {
  // Simplified FAO-56 Penman-Monteith reference ET₀ (in/day)
  // Convert imperial inputs to metric for internal calculation
  const temperatureC = (temperatureF - 32.0) * 5.0 / 9.0;
  const windMps = windMph / 2.23694;

  // Psychrometric constant (kPa/°C)
  const atmosphericPressure = 101.3 * Math.pow((293.0 - 0.0065 * elevationM) / 293.0, 5.26);
  const gamma = 0.000665 * atmosphericPressure;

  // Saturation vapor pressure (kPa) — Tetens formula
  const eSat = 0.6108 * Math.exp((17.27 * temperatureC) / (temperatureC + 237.3));

  // Actual vapor pressure from relative humidity
  const eAct = eSat * (humidityPct / 100.0);

  // Vapor pressure deficit
  const vpd = Math.max(0.0, eSat - eAct);

  // Slope of saturation vapor pressure curve (kPa/°C)
  const delta = (4098.0 * eSat) / Math.pow(temperatureC + 237.3, 2);

  // Net radiation approximation: Rn ≈ 0.77 * Rs (albedo = 0.23 for grass)
  const rn = 0.77 * solarRadiationMjM2;

  // FAO-56 Penman-Monteith equation (soil heat flux G = 0 for daily timestep)
  const numerator = (0.408 * delta * rn) + (gamma * (900.0 / (temperatureC + 273.0)) * windMps * vpd);
  const denominator = delta + gamma * (1.0 + 0.34 * windMps);

  const et0Mm = denominator > 0 ? numerator / denominator : 0.0;
  const et0In = Math.max(0.0, et0Mm) * 0.039370;
  return round(et0In, 4);
}

// ── Moisture trajectory ────────────────────────────────────────────────────────

export function predictMoistureTrajectory(inputs, etIn) {
  const retention = TEXTURE_RETENTION[inputs.soilTexture] ?? 1;
  const drainage = DRAINAGE_FACTOR[inputs.drainageClass] ?? 1;
  const irrigationEfficiency = IRRIGATION_EFFICIENCY[inputs.irrigationType] ?? 0.82;
  const trendOne = inputs.currentMoisture - inputs.lagOneMoisture;
  const trendTwo = inputs.lagOneMoisture - inputs.lagTwoMoisture;
  const trendMomentum = trendOne * 0.55 + trendTwo * 0.25;
  const stageLoad = (GROWTH_STAGE_MODIFIER[inputs.growthStage] ?? 0.1) * 0.05;
  const drynessPulse =
    etIn * 0.13208 +                                              // was etMm * 0.0052 (× 25.4)
    Math.max(0, inputs.temperatureF - 86) * 0.000722 +           // was (°C - 30) * 0.0013 (÷ 1.8)
    inputs.windMph * 0.000402 +                                   // was windMps * 0.0009 (÷ 2.23694)
    inputs.slopePct * 0.0011 +
    stageLoad;
  const recharge =
    inputs.precipitationIn * 0.08128 +                           // was precipitationMm * 0.0032 (× 25.4)
    inputs.recentIrrigation24h * irrigationEfficiency * 0.06096 + // was * 0.0024 (× 25.4)
    inputs.recentIrrigation72h * irrigationEfficiency * 0.02286;  // was * 0.0009 (× 25.4)
  const effectiveDrying = (drynessPulse * drainage) / retention;
  const resilience = (inputs.infiltrationRate / 24) * 0.015240;  // was * 0.0006 (× 25.4)

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

// ── Stress probability ─────────────────────────────────────────────────────────

export function computeStressProbability({ predictedMoisture48h, dryThreshold, estimatedEtIn, precipitationIn, growthStage }) {
  const stageModifier = GROWTH_STAGE_MODIFIER[growthStage] ?? 0.1;
  const moistureGap = dryThreshold - predictedMoisture48h;
  const score = moistureGap * 18 + estimatedEtIn * 3.048 - precipitationIn * 2.032 + stageModifier;
  return round(clip(1 / (1 + Math.exp(-score)), 0.01, 0.99), 3);
}

// ── Irrigation plan ────────────────────────────────────────────────────────────

export function computeBudgetCap(fieldAreaAcres, budgetDollars) {
  if (fieldAreaAcres <= 0) {
    return 0;
  }
  // Typical irrigation cost $50-$100/acre ÷ 12 in/year × 20 events ≈ $83/in-acre
  const BUDGET_CONSTANT = 82.25; // $/in-acre
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

export function scoreConfidence({ forecast48h, dryThreshold, timingWindow, modelRmse = 0.12, sensorCount = 1 }) {
  const base = Math.max(0.2, 1 - Math.min(modelRmse, 0.35) / 0.35);
  const thresholdMargin = Math.abs(forecast48h - dryThreshold);
  const marginBonus = Math.min(0.2, thresholdMargin / 0.15);
  const sensorPenalty = sensorCount >= 4 ? 0 : 0.08;
  const timingPenalty = timingWindow === "next available permitted window" ? 0.05 : 0;
  return round(clip(base + marginBonus - sensorPenalty - timingPenalty, 0.05, 0.99), 3);
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
  // Flood (68%) requires more gross water than pivot (82%) to deliver same net amount to roots
  const efficiency = IRRIGATION_EFFICIENCY[inputs.irrigationType] || 0.82;
  const grossAmountNeeded = rawAmountIn / efficiency;

  const constraints = {
    need: grossAmountNeeded,
    maxVolume: inputs.maxIrrigationVolume,
    pumpCapacity: inputs.pumpCapacity * allowedHours(inputs.waterWindow),
    budget: computeBudgetCap(inputs.fieldAreaAcres, inputs.budgetDollars),
    infiltration: inputs.infiltrationRate * 2.5,
  };
  const recommendedAmountIn = Math.min(
    constraints.need,
    constraints.maxVolume,
    constraints.pumpCapacity,
    constraints.budget,
    constraints.infiltration,
  );
  const bindingConstraint = Object.entries(constraints).reduce((min, curr) => curr[1] < min[1] ? curr : min)[0];
  const gaps = Object.fromEntries(
    Object.entries(constraints).map(([k, v]) => [k, round(v - recommendedAmountIn, 3)]),
  );

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
    }),
    stressProbability,
    thresholds,
    bindingConstraint,
    constraints,
    gaps,
  };
}

// ── Narrative builders ─────────────────────────────────────────────────────────

export function buildDrivers(inputs, predicted, stressProbability, estimatedEtIn) {
  const drivers = [];
  if (estimatedEtIn >= 0.217) {  // ~5.5 mm/day in inches
    drivers.push("High evapotranspiration is pulling moisture down quickly.");
  }
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  if (inputs.currentMoisture <= thresholds.dry + 0.04) {
    drivers.push("Current soil moisture is already near the crop stress band.");
  }
  if (inputs.precipitationIn < 0.059) {  // ~1.5 mm in inches
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

// ── UI tone ────────────────────────────────────────────────────────────────────

export function recommendationTone(run) {
  return run.decision === "water"
    ? {
        spotlight: "spotlight-water",
        pill: "bg-[var(--accent-warm-soft)] text-[var(--accent-warm)]",
        amount: "text-[var(--accent-warm)]",
      }
    : {
        spotlight: "spotlight-wait",
        pill: "bg-[var(--accent-mint-soft)] text-[var(--accent-mint)]",
        amount: "text-[var(--accent-mint)]",
      };
}

// ── Copy serializer ────────────────────────────────────────────────────────────

export function serializeRunForCopy(run) {
  const lines = [
    `Run: ${run.title}`,
    `Timestamp: ${formatTimestamp(run.timestamp)}`,
    `Decision: ${run.decision.toUpperCase()}`,
    `Recommended amount: ${run.recommendedAmountIn.toFixed(2)} in`,
    `Timing window: ${formatWindow(run.timingWindow)}`,
    `Heuristic confidence: ${formatPercent(run.confidenceScore)}`,
    `Stress probability: ${formatPercent(run.stressProbability)}`,
    `Reference ET: ${run.estimatedEtIn.toFixed(2)} in/day`,
    `Forecast 24h: ${run.predicted.moisture24h.toFixed(2)}`,
    `Forecast 48h: ${run.predicted.moisture48h.toFixed(2)}`,
    `Forecast 72h: ${run.predicted.moisture72h.toFixed(2)}`,
    "",
    "Drivers:",
    ...run.drivers.map((driver) => `- ${driver}`),
    "",
    "Prompt:",
    run.prompt,
  ];
  if (run.recommendationAdjustment) {
    lines.push("");
    lines.push(`Base recommendation: ${run.recommendationAdjustment.baseRecommendationIn.toFixed(2)} in`);
    lines.push(`Adjustment factor: ${run.recommendationAdjustment.adjustmentFactor.toFixed(2)}x`);
    lines.push(`Adjustment reason: ${run.recommendationAdjustment.reason}`);
  }
  if (run.regionalInsights) {
    lines.push(`Regional success rate: ${Math.round(run.regionalInsights.successRate * 100)}%`);
    lines.push(`Regional samples: ${run.regionalInsights.totalSamples}`);
  }
  if (run.sourceLabel) {
    lines.push(`Recommendation source: ${run.sourceLabel}`);
  }
  return lines.join("\n");
}
