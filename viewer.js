const SOIL_THRESHOLDS = {
  sand: { dry: 0.12, wet: 0.28 },
  loam: { dry: 0.18, wet: 0.35 },
  clay: { dry: 0.22, wet: 0.4 },
};

const ROOT_ZONE_FACTORS = {
  sand: 110,
  loam: 135,
  clay: 155,
};

const IRRIGATION_EFFICIENCY = {
  pivot: 0.82,
  drip: 0.93,
  flood: 0.68,
};

const GROWTH_STAGE_MODIFIER = {
  emergence: 0.05,
  vegetative: 0.1,
  flowering: 0.18,
  grain_fill: 0.14,
  maturity: 0.02,
};

const TEXTURE_RETENTION = {
  sand: 0.91,
  loam: 1,
  clay: 1.08,
};

const DRAINAGE_FACTOR = {
  poor: 0.88,
  moderate: 1,
  well: 1.12,
};

const PRESETS = {
  heatwave: {
    fieldName: "North Pivot 7",
    fieldAreaHa: 24,
    cropType: "corn",
    growthStage: "flowering",
    soilTexture: "loam",
    drainageClass: "moderate",
    infiltrationRate: 12,
    slopePct: 2.5,
    currentMoisture: 0.2,
    lagOneMoisture: 0.21,
    lagTwoMoisture: 0.22,
    temperatureC: 34,
    humidityPct: 26,
    windMps: 4.6,
    precipitationMm: 0,
    solarRadiationMjM2: 28,
    irrigationType: "pivot",
    pumpCapacity: 6,
    maxIrrigationVolume: 18,
    budgetDollars: 3000,
    recentIrrigation24h: 6,
    recentIrrigation72h: 10,
    waterWindow: ["tonight", "tomorrow_morning"],
    energyWindow: ["tonight"],
  },
  balanced: {
    fieldName: "South Bench 2",
    fieldAreaHa: 18,
    cropType: "soybean",
    growthStage: "vegetative",
    soilTexture: "loam",
    drainageClass: "moderate",
    infiltrationRate: 11,
    slopePct: 1.7,
    currentMoisture: 0.27,
    lagOneMoisture: 0.275,
    lagTwoMoisture: 0.278,
    temperatureC: 27,
    humidityPct: 52,
    windMps: 2.8,
    precipitationMm: 2.8,
    solarRadiationMjM2: 21,
    irrigationType: "drip",
    pumpCapacity: 4.5,
    maxIrrigationVolume: 12,
    budgetDollars: 2200,
    recentIrrigation24h: 2,
    recentIrrigation72h: 5,
    waterWindow: ["tomorrow_morning", "tomorrow_night"],
    energyWindow: ["tomorrow_morning"],
  },
  rain: {
    fieldName: "Creek Flat 3",
    fieldAreaHa: 31,
    cropType: "potato",
    growthStage: "grain_fill",
    soilTexture: "clay",
    drainageClass: "poor",
    infiltrationRate: 7,
    slopePct: 1.2,
    currentMoisture: 0.31,
    lagOneMoisture: 0.305,
    lagTwoMoisture: 0.298,
    temperatureC: 23,
    humidityPct: 66,
    windMps: 2.2,
    precipitationMm: 11,
    solarRadiationMjM2: 16,
    irrigationType: "pivot",
    pumpCapacity: 5.8,
    maxIrrigationVolume: 16,
    budgetDollars: 3200,
    recentIrrigation24h: 0,
    recentIrrigation72h: 4,
    waterWindow: ["tonight", "tomorrow_night"],
    energyWindow: ["tomorrow_night"],
  },
};

const HISTORY_KEY = "helios-pages-history";

const form = document.querySelector("#helios-form");
const presetButtons = document.querySelectorAll("[data-preset]");
const heroDecision = document.querySelector("#hero-decision");
const heroAmount = document.querySelector("#hero-amount");
const heroWindow = document.querySelector("#hero-window");
const heroConfidence = document.querySelector("#hero-confidence");
const heroSummary = document.querySelector("#hero-summary");
const decisionOutput = document.querySelector("#decision-output");
const decisionDetail = document.querySelector("#decision-detail");
const amountOutput = document.querySelector("#amount-output");
const windowOutput = document.querySelector("#window-output");
const confidenceOutput = document.querySelector("#confidence-output");
const stressOutput = document.querySelector("#stress-output");
const etOutput = document.querySelector("#et-output");
const forecast24 = document.querySelector("#forecast-24");
const forecast48 = document.querySelector("#forecast-48");
const forecast72 = document.querySelector("#forecast-72");
const stressFill = document.querySelector("#stress-fill");
const etFill = document.querySelector("#et-fill");
const driversList = document.querySelector("#drivers-list");
const recommendationSummaryNode = document.querySelector("#recommendation-summary");
const chart = document.querySelector("#forecast-chart");
const historyList = document.querySelector("#history-list");
const saveScenarioButton = document.querySelector("#save-scenario");

function round(value, decimals = 1) {
  return Number(value.toFixed(decimals));
}

function clip(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function estimateReferenceEtMm({ temperatureC, humidityPct, windMps, solarRadiationMjM2 }) {
  const humidityFactor = Math.max(0.1, 1 - (humidityPct / 100) * 0.65);
  const temperatureFactor = Math.max(0, (temperatureC + 5) / 25);
  const windFactor = 1 + Math.min(windMps, 12) * 0.08;
  const solarFactor = solarRadiationMjM2 * 0.11;
  return round(Math.max(0, solarFactor * humidityFactor * windFactor * temperatureFactor), 3);
}

function readCheckedValues(name) {
  return [...form.querySelectorAll(`input[name="${name}"]:checked`)].map((input) => input.value);
}

function getInputs() {
  const data = new FormData(form);
  return {
    fieldName: String(data.get("fieldName")),
    fieldAreaHa: Number(data.get("fieldAreaHa")),
    cropType: String(data.get("cropType")),
    growthStage: String(data.get("growthStage")),
    soilTexture: String(data.get("soilTexture")),
    drainageClass: String(data.get("drainageClass")),
    infiltrationRate: Number(data.get("infiltrationRate")),
    slopePct: Number(data.get("slopePct")),
    currentMoisture: Number(data.get("currentMoisture")),
    lagOneMoisture: Number(data.get("lagOneMoisture")),
    lagTwoMoisture: Number(data.get("lagTwoMoisture")),
    temperatureC: Number(data.get("temperatureC")),
    humidityPct: Number(data.get("humidityPct")),
    windMps: Number(data.get("windMps")),
    precipitationMm: Number(data.get("precipitationMm")),
    solarRadiationMjM2: Number(data.get("solarRadiationMjM2")),
    irrigationType: String(data.get("irrigationType")),
    pumpCapacity: Number(data.get("pumpCapacity")),
    maxIrrigationVolume: Number(data.get("maxIrrigationVolume")),
    budgetDollars: Number(data.get("budgetDollars")),
    recentIrrigation24h: Number(data.get("recentIrrigation24h")),
    recentIrrigation72h: Number(data.get("recentIrrigation72h")),
    waterWindow: readCheckedValues("waterWindow"),
    energyWindow: readCheckedValues("energyWindow"),
  };
}

function predictMoistureTrajectory(inputs, etMm) {
  const retention = TEXTURE_RETENTION[inputs.soilTexture] ?? 1;
  const drainage = DRAINAGE_FACTOR[inputs.drainageClass] ?? 1;
  const irrigationEfficiency = IRRIGATION_EFFICIENCY[inputs.irrigationType] ?? 0.82;
  const trendOne = inputs.currentMoisture - inputs.lagOneMoisture;
  const trendTwo = inputs.lagOneMoisture - inputs.lagTwoMoisture;
  const trendMomentum = trendOne * 0.55 + trendTwo * 0.25;
  const stageLoad = (GROWTH_STAGE_MODIFIER[inputs.growthStage] ?? 0.1) * 0.05;
  const drynessPulse =
    etMm * 0.0052 +
    Math.max(0, inputs.temperatureC - 30) * 0.0013 +
    inputs.windMps * 0.0009 +
    inputs.slopePct * 0.0011 +
    stageLoad;
  const recharge =
    inputs.precipitationMm * 0.0032 +
    inputs.recentIrrigation24h * irrigationEfficiency * 0.0024 +
    inputs.recentIrrigation72h * irrigationEfficiency * 0.0009;
  const effectiveDrying = (drynessPulse * drainage) / retention;
  const resilience = (inputs.infiltrationRate / 24) * 0.0006;

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

function computeStressProbability({ predictedMoisture48h, dryThreshold, estimatedEtMm, precipitationMm, growthStage }) {
  const stageModifier = GROWTH_STAGE_MODIFIER[growthStage] ?? 0.1;
  const moistureGap = dryThreshold - predictedMoisture48h;
  const score = moistureGap * 18 + estimatedEtMm * 0.12 - precipitationMm * 0.08 + stageModifier;
  return round(clip(1 / (1 + Math.exp(-score)), 0.01, 0.99), 3);
}

function computeBudgetCap(fieldAreaHa, budgetDollars) {
  if (fieldAreaHa <= 0) {
    return 0;
  }
  return budgetDollars / (8 * fieldAreaHa);
}

function allowedHours(waterWindows) {
  return Math.max(1, Math.min(12, waterWindows.length * 3));
}

function selectTimingWindow(waterWindows, energyWindows, needsWater) {
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

function scoreConfidence({ forecast48h, dryThreshold, timingWindow }) {
  const base = Math.max(0.2, 1 - Math.min(0.12, 0.35) / 0.35);
  const thresholdMargin = Math.abs(forecast48h - dryThreshold);
  const marginBonus = Math.min(0.2, thresholdMargin / 0.15);
  const timingPenalty = timingWindow === "next available permitted window" ? 0.05 : 0;
  return round(clip(base + marginBonus - timingPenalty, 0.05, 0.99), 3);
}

function generateIrrigationPlan(inputs, predicted, stressProbability, estimatedEtMm) {
  const thresholds = SOIL_THRESHOLDS[inputs.soilTexture] ?? SOIL_THRESHOLDS.loam;
  const predicted48h = predicted.moisture48h;
  const needsWater = predicted48h < thresholds.dry;
  const timingWindow = selectTimingWindow(inputs.waterWindow, inputs.energyWindow, needsWater);
  const targetMoisture = Math.min(thresholds.wet, thresholds.dry + 0.08 + estimatedEtMm * 0.002);
  const deficit = Math.max(0, targetMoisture - predicted48h);
  const rawAmountMm = Math.max(
    0,
    deficit * (ROOT_ZONE_FACTORS[inputs.soilTexture] ?? ROOT_ZONE_FACTORS.loam) - inputs.precipitationMm * 0.7,
  );
  const recommendedAmountMm = Math.min(
    rawAmountMm,
    inputs.maxIrrigationVolume,
    inputs.pumpCapacity * allowedHours(inputs.waterWindow),
    computeBudgetCap(inputs.fieldAreaHa, inputs.budgetDollars),
    inputs.infiltrationRate * 2.5,
  );

  return {
    decision: needsWater ? "water" : "wait",
    recommendedAmountMm: round(needsWater ? recommendedAmountMm : 0, 1),
    timingWindow,
    confidenceScore: scoreConfidence({
      forecast48h: predicted48h,
      dryThreshold: thresholds.dry,
      timingWindow,
    }),
    stressProbability,
    thresholds,
  };
}

function buildDrivers(inputs, predicted, stressProbability, estimatedEtMm) {
  const drivers = [];
  if (estimatedEtMm >= 5.5) {
    drivers.push("High evapotranspiration is pulling moisture down quickly.");
  }
  if (inputs.currentMoisture <= SOIL_THRESHOLDS[inputs.soilTexture].dry + 0.04) {
    drivers.push("Current soil moisture is already near the crop stress band.");
  }
  if (inputs.precipitationMm < 1.5) {
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
  return drivers.slice(0, 3).length > 0 ? drivers.slice(0, 3) : ["Conditions are stable enough to keep watching instead of watering now."];
}

function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

function formatWindow(value) {
  return value.replaceAll("_", " ");
}

function buildSummary(inputs, predicted, plan) {
  const action =
    plan.decision === "water"
      ? `Apply ${plan.recommendedAmountMm.toFixed(1)} mm during ${formatWindow(plan.timingWindow)}.`
      : "Hold irrigation and reassess after the next weather update.";
  return `${inputs.fieldName} is forecast to move from ${inputs.currentMoisture.toFixed(2)} now to ${predicted.moisture48h.toFixed(2)} in 48 hours. ${action}`;
}

function renderChart(currentMoisture, predicted, thresholds) {
  const points = [
    { label: "Now", value: currentMoisture },
    { label: "24h", value: predicted.moisture24h },
    { label: "48h", value: predicted.moisture48h },
    { label: "72h", value: predicted.moisture72h },
  ];
  const width = 640;
  const height = 280;
  const margin = { top: 24, right: 26, bottom: 48, left: 42 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const minValue = 0.05;
  const maxValue = 0.45;

  const x = (index) => margin.left + (innerWidth / (points.length - 1)) * index;
  const y = (value) => margin.top + (1 - (value - minValue) / (maxValue - minValue)) * innerHeight;
  const linePoints = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");
  const areaPath = `${linePoints} ${x(points.length - 1)},${height - margin.bottom} ${x(0)},${height - margin.bottom}`;
  const dryY = y(thresholds.dry);

  chart.innerHTML = `
    <line class="chart-grid-line" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" />
    <line class="chart-grid-line" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" />
    <line class="chart-threshold" x1="${margin.left}" y1="${dryY}" x2="${width - margin.right}" y2="${dryY}" />
    <text class="chart-axis-label" x="${width - margin.right - 82}" y="${dryY - 10}">Dry threshold</text>
    <polygon class="chart-area" points="${areaPath}" />
    <polyline class="chart-line" points="${linePoints}" />
    ${points
      .map(
        (point, index) => `
          <circle class="chart-point ${index === 0 ? "current" : ""}" cx="${x(index)}" cy="${y(point.value)}" r="7" />
          <text class="chart-point-label" x="${x(index) - 10}" y="${height - 18}">${point.label}</text>
          <text class="chart-point-label" x="${x(index) - 14}" y="${y(point.value) - 14}">${point.value.toFixed(2)}</text>
        `,
      )
      .join("")}
  `;
}

function updateOutputs(inputs, predicted, plan, estimatedEtMm, drivers) {
  const summary = buildSummary(inputs, predicted, plan);
  const decisionText = plan.decision === "water" ? "Water" : "Wait";
  const decisionClass = plan.decision === "water" ? "alert" : "success";

  heroDecision.textContent = decisionText;
  heroDecision.className = `headline-decision ${decisionClass}`;
  heroAmount.textContent = `${plan.recommendedAmountMm.toFixed(1)} mm`;
  heroWindow.textContent = formatWindow(plan.timingWindow);
  heroConfidence.textContent = formatPercent(plan.confidenceScore);
  heroSummary.textContent = summary;

  decisionOutput.textContent = decisionText;
  decisionOutput.className = decisionClass;
  decisionDetail.textContent = summary;
  amountOutput.textContent = `${plan.recommendedAmountMm.toFixed(1)} mm`;
  windowOutput.textContent = formatWindow(plan.timingWindow);
  confidenceOutput.textContent = formatPercent(plan.confidenceScore);
  stressOutput.textContent = formatPercent(plan.stressProbability);
  etOutput.textContent = `${estimatedEtMm.toFixed(1)} mm/day`;
  forecast24.textContent = predicted.moisture24h.toFixed(2);
  forecast48.textContent = predicted.moisture48h.toFixed(2);
  forecast72.textContent = predicted.moisture72h.toFixed(2);
  stressFill.style.width = `${Math.round(plan.stressProbability * 100)}%`;
  etFill.style.width = `${Math.min(100, Math.round((estimatedEtMm / 8) * 100))}%`;
  driversList.innerHTML = drivers.map((driver) => `<li>${driver}</li>`).join("");
  recommendationSummaryNode.textContent = summary;
  renderChart(inputs.currentMoisture, predicted, plan.thresholds);
}

function evaluateScenario() {
  const inputs = getInputs();
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
  updateOutputs(inputs, predicted, plan, estimatedEtMm, drivers);
  return {
    timestamp: new Date().toLocaleString(),
    fieldName: inputs.fieldName,
    decision: plan.decision,
    recommendedAmountMm: plan.recommendedAmountMm,
    timingWindow: plan.timingWindow,
    confidenceScore: plan.confidenceScore,
  };
}

function readHistory() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeHistory(history) {
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 6)));
}

function renderHistory() {
  const history = readHistory();
  if (history.length === 0) {
    historyList.innerHTML = `<div class="history-item"><strong>No saved scenarios yet</strong><span>Generate a recommendation, then click Save Scenario.</span></div>`;
    return;
  }

  historyList.innerHTML = history
    .map(
      (entry) => `
        <article class="history-item">
          <strong>${entry.fieldName} • ${entry.decision.toUpperCase()}</strong>
          <span>${entry.timestamp}</span>
          <span>${entry.recommendedAmountMm.toFixed(1)} mm • ${formatWindow(entry.timingWindow)} • ${formatPercent(entry.confidenceScore)}</span>
        </article>
      `,
    )
    .join("");
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) {
    return;
  }

  for (const [key, value] of Object.entries(preset)) {
    if (Array.isArray(value)) {
      continue;
    }
    const field = form.elements.namedItem(key);
    if (field && "value" in field) {
      field.value = String(value);
    }
  }

  form.querySelectorAll('input[name="waterWindow"]').forEach((checkbox) => {
    checkbox.checked = preset.waterWindow.includes(checkbox.value);
  });
  form.querySelectorAll('input[name="energyWindow"]').forEach((checkbox) => {
    checkbox.checked = preset.energyWindow.includes(checkbox.value);
  });

  evaluateScenario();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  evaluateScenario();
});

form.addEventListener("input", () => {
  evaluateScenario();
});

saveScenarioButton.addEventListener("click", () => {
  const history = readHistory();
  history.unshift(evaluateScenario());
  writeHistory(history);
  renderHistory();
});

presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    applyPreset(button.dataset.preset);
  });
});

applyPreset("heatwave");
renderHistory();
