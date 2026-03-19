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

const PAGE_TITLES = {
  dashboard: "Dashboard",
  "run-analysis": "Run Analysis",
  history: "History",
  saved: "Saved Runs",
  settings: "Settings",
};

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "layout" },
  { id: "run-analysis", label: "Run Analysis", icon: "sparkles" },
  { id: "history", label: "History", icon: "history" },
  { id: "saved", label: "Saved Runs", icon: "bookmark" },
  { id: "settings", label: "Settings", icon: "settings" },
];

const RUN_HISTORY_KEY = "helios-pages-history";
const SAVED_RUNS_KEY = "helios-pages-saved-runs";
const THEME_KEY = "helios-dashboard-theme";

const DEFAULT_RUNTIME_CONFIG = {
  mode: "demo",
  apiBaseUrl: "",
  disclaimer:
    "Demo mode uses browser-side prototype logic only. It does not call a live backend or store feedback in the project database.",
};

function normalizeRuntimeConfig(config) {
  const mode = config?.mode === "live" ? "live" : "demo";
  return {
    mode,
    apiBaseUrl: typeof config?.apiBaseUrl === "string" ? config.apiBaseUrl.trim().replace(/\/+$/, "") : "",
    disclaimer:
      typeof config?.disclaimer === "string" && config.disclaimer.trim().length > 0
        ? config.disclaimer.trim()
        : DEFAULT_RUNTIME_CONFIG.disclaimer,
  };
}

const runtimeConfig = normalizeRuntimeConfig(window.HELIOS_CONFIG || DEFAULT_RUNTIME_CONFIG);

const DEFAULT_FORM = {
  analysisPrompt:
    "Review the next 72 hours of moisture risk and recommend whether this field should be irrigated now or held.",
  model: "Helios Core",
  autoSave: false,
  includeNotes: true,
  farmId: "north-pivot-7",
  fieldName: "North Pivot 7",
  fieldAreaHa: 24,
  cropType: "corn",
  growthStage: "flowering",
  soilTexture: "loam",
  drainageClass: "moderate",
  infiltrationRate: 12,
  slopePct: 2.5,
  locationLat: 43.615,
  locationLon: -116.202,
  currentMoisture: 0.2,
  lagOneMoisture: 0.21,
  lagTwoMoisture: 0.22,
  temperatureC: 31,
  humidityPct: 38,
  windMps: 3.8,
  precipitationMm: 0,
  solarRadiationMjM2: 24,
  irrigationType: "pivot",
  pumpCapacity: 6,
  maxIrrigationVolume: 18,
  budgetDollars: 2800,
  recentIrrigation24h: 8,
  recentIrrigation72h: 12,
  waterWindow: ["tonight", "tomorrow_morning"],
  energyWindow: ["tonight", "tomorrow_night"],
};

const PRESETS = {
  heatwave: {
    ...DEFAULT_FORM,
    analysisPrompt:
      "Assess a heat-wave scenario. Prioritize yield protection and the cheapest feasible irrigation window.",
    farmId: "north-pivot-7",
    fieldName: "North Pivot 7",
    locationLat: 43.615,
    locationLon: -116.202,
    temperatureC: 34,
    humidityPct: 26,
    windMps: 4.6,
    precipitationMm: 0,
    solarRadiationMjM2: 28,
    currentMoisture: 0.2,
    lagOneMoisture: 0.21,
    lagTwoMoisture: 0.22,
    recentIrrigation24h: 6,
    recentIrrigation72h: 10,
    budgetDollars: 3000,
    waterWindow: ["tonight", "tomorrow_morning"],
    energyWindow: ["tonight"],
  },
  balanced: {
    ...DEFAULT_FORM,
    analysisPrompt:
      "Check whether the field can safely wait through a mild day while preserving water and energy budget.",
    model: "Helios Balanced",
    farmId: "south-bench-2",
    fieldName: "South Bench 2",
    locationLat: 43.601,
    locationLon: -116.145,
    fieldAreaHa: 18,
    cropType: "soybean",
    growthStage: "vegetative",
    irrigationType: "drip",
    currentMoisture: 0.27,
    lagOneMoisture: 0.275,
    lagTwoMoisture: 0.278,
    temperatureC: 27,
    humidityPct: 52,
    windMps: 2.8,
    precipitationMm: 2.8,
    solarRadiationMjM2: 21,
    pumpCapacity: 4.5,
    maxIrrigationVolume: 12,
    budgetDollars: 2200,
    recentIrrigation24h: 2,
    recentIrrigation72h: 5,
    waterWindow: ["tomorrow_morning", "tomorrow_night"],
    energyWindow: ["tomorrow_morning"],
  },
  rain: {
    ...DEFAULT_FORM,
    analysisPrompt:
      "Forecast whether incoming rain and higher retained soil water are enough to skip the next irrigation cycle.",
    model: "Helios Conservative",
    farmId: "creek-flat-3",
    fieldName: "Creek Flat 3",
    locationLat: 43.589,
    locationLon: -116.248,
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
    pumpCapacity: 5.8,
    maxIrrigationVolume: 16,
    budgetDollars: 3200,
    recentIrrigation24h: 0,
    recentIrrigation72h: 4,
    waterWindow: ["tonight", "tomorrow_night"],
    energyWindow: ["tomorrow_night"],
  },
};

const app = document.querySelector("#app");

const state = {
  activePage: "run-analysis",
  theme: localStorage.getItem(THEME_KEY) || "dark",
  form: { ...DEFAULT_FORM },
  runHistory: loadStoredArray(RUN_HISTORY_KEY),
  savedRuns: loadStoredArray(SAVED_RUNS_KEY),
  latestRun: null,
  analysis: {
    status: isLiveApiMode()
      ? "Live API mode is configured. Helios will request a recommendation from the backend."
      : runtimeConfig.disclaimer,
    error: "",
    submitting: false,
    source: isLiveApiMode() ? "api" : "demo",
  },
  feedbackForm: {
    open: false,
    outcome: "SUCCESS",
    yieldDelta: "",
    notes: "",
    status: "",
    error: "",
    submitting: false,
  },
  analysisConsoleOpen: false,
};

if (state.runHistory.length > 0) {
  state.latestRun = state.runHistory[0];
}

applyTheme();
renderApp();

function loadStoredArray(key) {
  try {
    const value = window.localStorage.getItem(key);
    return value ? JSON.parse(value).map(normalizeRun).filter(Boolean) : [];
  } catch {
    return [];
  }
}

function normalizeRun(run) {
  if (!run || typeof run !== "object") {
    return null;
  }
  const inputSnapshot = run.inputSnapshot || {
    fieldName: run.fieldName || "Untitled field",
  };
  const predicted = run.predicted || {
    moisture24h: 0,
    moisture48h: 0,
    moisture72h: 0,
  };
  const normalized = {
    id: run.id || `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: run.title || `${inputSnapshot.fieldName} • Run Analysis`,
    timestamp: run.timestamp || new Date().toISOString(),
    prompt: run.prompt || "",
    decision: run.decision || "wait",
    recommendedAmountMm: Number(run.recommendedAmountMm || 0),
    timingWindow: run.timingWindow || "monitor next forecast cycle",
    confidenceScore: Number(run.confidenceScore || 0),
    stressProbability: Number(run.stressProbability || 0),
    estimatedEtMm: Number(run.estimatedEtMm || 0),
    predicted,
    drivers: Array.isArray(run.drivers) ? run.drivers : [],
    summary: run.summary || "",
    inputSnapshot,
    regionalInsights: run.regionalInsights || null,
    recommendationAdjustment: run.recommendationAdjustment || null,
    sourceLabel: run.sourceLabel || "",
  };
  normalized.copyText = run.copyText || serializeRunForCopy(normalized);
  return normalized;
}

function persistState() {
  window.localStorage.setItem(RUN_HISTORY_KEY, JSON.stringify(state.runHistory));
  window.localStorage.setItem(SAVED_RUNS_KEY, JSON.stringify(state.savedRuns));
  window.localStorage.setItem(THEME_KEY, state.theme);
}

function applyTheme() {
  document.body.classList.toggle("theme-light", state.theme === "light");
}

function isLiveApiMode() {
  return runtimeConfig.mode === "live";
}

function apiUrl(path) {
  return runtimeConfig.apiBaseUrl ? `${runtimeConfig.apiBaseUrl}${path}` : path;
}

async function readJsonResponse(response) {
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

function round(value, decimals = 1) {
  return Number(value.toFixed(decimals));
}

function clip(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

function formatWindow(value) {
  return value.replaceAll("_", " ");
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function icon(name, className = "h-5 w-5") {
  const icons = {
    layout:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>`,
    sparkles:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z"/><path d="M19 14l.9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14z"/><path d="M5 14l.7 1.6L7.3 16l-1.6.7L5 18.3l-.7-1.6L2.7 16l1.6-.4L5 14z"/></svg>`,
    history:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 7v5l3 2"/></svg>`,
    bookmark:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4h12a1 1 0 0 1 1 1v15l-7-4-7 4V5a1 1 0 0 1 1-1z"/></svg>`,
    settings:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.06.06a2 2 0 1 1-2.82 2.82l-.06-.06a1.8 1.8 0 0 0-1.98-.36 1.8 1.8 0 0 0-1.1 1.64V21a2 2 0 1 1-4 0v-.09a1.8 1.8 0 0 0-1.1-1.64 1.8 1.8 0 0 0-1.98.36l-.06.06a2 2 0 1 1-2.82-2.82l.06-.06A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.64-1.1H2.9a2 2 0 1 1 0-4h.09a1.8 1.8 0 0 0 1.64-1.1 1.8 1.8 0 0 0-.36-1.98l-.06-.06A2 2 0 1 1 7.03 4l.06.06a1.8 1.8 0 0 0 1.98.36h.01A1.8 1.8 0 0 0 10.18 2.8V2.7a2 2 0 1 1 4 0v.09a1.8 1.8 0 0 0 1.1 1.64 1.8 1.8 0 0 0 1.98-.36l.06-.06A2 2 0 1 1 20.14 7l-.06.06a1.8 1.8 0 0 0-.36 1.98v.01a1.8 1.8 0 0 0 1.64 1.1h.09a2 2 0 1 1 0 4h-.09a1.8 1.8 0 0 0-1.64 1.1z"/></svg>`,
    github:
      `<svg class="${className}" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.65.5.5 5.65.5 12A11.5 11.5 0 0 0 8.36 22.94c.58.11.79-.25.79-.56v-2.02c-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.71.08-.71 1.17.08 1.78 1.2 1.78 1.2 1.03 1.78 2.71 1.27 3.37.97.1-.75.4-1.27.73-1.57-2.55-.29-5.23-1.27-5.23-5.67 0-1.25.45-2.27 1.19-3.07-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.18 1.18a10.92 10.92 0 0 1 5.8 0c2.21-1.5 3.18-1.18 3.18-1.18.63 1.58.23 2.75.11 3.04.74.8 1.19 1.82 1.19 3.07 0 4.41-2.69 5.37-5.25 5.66.41.36.77 1.06.77 2.14v3.18c0 .31.21.68.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg>`,
    sun:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M4.93 4.93l1.77 1.77M17.3 17.3l1.77 1.77M2 12h2.5M19.5 12H22M4.93 19.07l1.77-1.77M17.3 6.7l1.77-1.77"/></svg>`,
    moon:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.79A9 9 0 0 1 11.21 3a7 7 0 1 0 9.79 9.79z"/></svg>`,
    copy:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    check:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m5 13 4 4L19 7"/></svg>`,
    user:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/></svg>`,
    chart:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5-6"/></svg>`,
    chevronDown:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 9 6 6 6-6"/></svg>`,
  };
  return icons[name] || "";
}

function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function estimateReferenceEtMm({ temperatureC, humidityPct, windMps, solarRadiationMjM2 }) {
  const humidityFactor = Math.max(0.1, 1 - (humidityPct / 100) * 0.65);
  const temperatureFactor = Math.max(0, (temperatureC + 5) / 25);
  const windFactor = 1 + Math.min(windMps, 12) * 0.08;
  const solarFactor = solarRadiationMjM2 * 0.11;
  return round(Math.max(0, solarFactor * humidityFactor * windFactor * temperatureFactor), 3);
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
  return drivers.slice(0, 3).length > 0
    ? drivers.slice(0, 3)
    : ["Conditions are stable enough to keep watching instead of watering now."];
}

function buildSummary(inputs, predicted, plan) {
  const action =
    plan.decision === "water"
      ? `Apply ${plan.recommendedAmountMm.toFixed(1)} mm during ${formatWindow(plan.timingWindow)}.`
      : "Hold irrigation and reassess after the next weather update.";
  return `${inputs.fieldName} is forecast to move from ${inputs.currentMoisture.toFixed(2)} now to ${predicted.moisture48h.toFixed(2)} in 48 hours. ${action}`;
}

function recommendationTone(run) {
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

function serializeRunForCopy(run) {
  const lines = [
    `Run: ${run.title}`,
    `Timestamp: ${formatTimestamp(run.timestamp)}`,
    `Decision: ${run.decision.toUpperCase()}`,
    `Recommended amount: ${run.recommendedAmountMm.toFixed(1)} mm`,
    `Timing window: ${formatWindow(run.timingWindow)}`,
    `Heuristic confidence: ${formatPercent(run.confidenceScore)}`,
    `Stress probability: ${formatPercent(run.stressProbability)}`,
    `Reference ET: ${run.estimatedEtMm.toFixed(1)} mm/day`,
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
    lines.push(`Base recommendation: ${run.recommendationAdjustment.baseRecommendationMm.toFixed(1)} mm`);
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

function buildPredictionRequest(inputs) {
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

function mapApiRun(inputs, response) {
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

function buildLocalRun(inputs) {
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

function storeRun(run) {
  state.latestRun = run;
  state.feedbackForm.open = false;
  state.feedbackForm.status = "";
  state.feedbackForm.error = "";
  state.feedbackForm.yieldDelta = "";
  state.feedbackForm.notes = "";
  state.runHistory.unshift(run);
  state.runHistory = state.runHistory.slice(0, 50);
  if (state.form.autoSave) {
    state.savedRuns.unshift(run);
    state.savedRuns = dedupeRuns(state.savedRuns).slice(0, 50);
  }
  persistState();
}

async function refreshRegionalInsights(run) {
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

async function evaluateScenario() {
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

function feedbackSummary(run) {
  if (!run?.regionalInsights) {
    return isLiveApiMode()
      ? "No comparable nearby farmer feedback is being used yet for this field."
      : "Demo mode does not use stored farmer feedback.";
  }
  const yieldText =
    run.regionalInsights.avgYieldDelta == null
      ? "Yield change data is still limited."
      : `Average yield change: ${Number(run.regionalInsights.avgYieldDelta).toFixed(1)}%.`;
  return `${Math.round(run.regionalInsights.successRate * 100)}% success across ${run.regionalInsights.totalSamples} nearby farms within ${Math.round(run.regionalInsights.radiusKm || 50)} km. Filters require the same crop, soil texture, and irrigation type. ${yieldText}`;
}

async function submitFeedback() {
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

function dedupeRuns(runs) {
  const seen = new Set();
  return runs.filter((run) => {
    if (seen.has(run.id)) {
      return false;
    }
    seen.add(run.id);
    return true;
  });
}

function saveLatestRun() {
  if (!state.latestRun) {
    return;
  }
  state.savedRuns.unshift(state.latestRun);
  state.savedRuns = dedupeRuns(state.savedRuns).slice(0, 50);
  persistState();
  renderApp();
}

function setPage(pageId) {
  state.activePage = pageId;
  renderApp();
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  applyTheme();
  persistState();
  renderApp();
}

function applyPreset(name) {
  if (!PRESETS[name]) {
    return;
  }
  state.form = { ...PRESETS[name] };
  state.activePage = "run-analysis";
  renderApp();
}

function updateFormField(name, value) {
  state.form[name] = value;
}

function updateArrayField(name, nextValue, checked) {
  const current = new Set(state.form[name]);
  if (checked) {
    current.add(nextValue);
  } else {
    current.delete(nextValue);
  }
  state.form[name] = [...current];
}

function copyText(value, trigger) {
  navigator.clipboard.writeText(value).then(() => {
    if (!trigger) {
      return;
    }
    trigger.innerHTML = `${icon("check", "h-4 w-4")} <span>Copied</span>`;
    window.setTimeout(() => {
      trigger.innerHTML = `${icon("copy", "h-4 w-4")} <span>Copy</span>`;
    }, 1200);
  }).catch(() => {
    if (!trigger) {
      return;
    }
    trigger.innerHTML = `${icon("copy", "h-4 w-4")} <span>Copy failed</span>`;
  });
}

function renderApp() {
  const showResultsPanel = state.activePage !== "run-analysis";
  app.innerHTML = `
    <div class="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <div class="grid min-h-screen ${showResultsPanel ? "grid-cols-[78px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_420px]" : "grid-cols-[78px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)]"}">
        ${Sidebar()}
        <div class="min-w-0">
          ${TopBar()}
          <main class="glass-grid min-h-[calc(100vh-65px)] px-4 py-4 sm:px-6 sm:py-6">
            ${renderPage()}
          </main>
        </div>
        ${showResultsPanel ? ResultsPanel() : ""}
      </div>
    </div>
  `;
  window.tailwind?.refresh?.();
  bindAppEvents();
  resizePromptInput();
}

function Sidebar() {
  return `
    <aside class="sticky top-0 flex h-screen flex-col border-r border-[var(--border)] bg-[var(--bg)]">
      <div class="flex h-16 items-center gap-3 border-b border-[var(--border)] px-4">
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] shadow-[var(--shadow)]">
          ${icon("sparkles")}
        </div>
        <div class="hidden xl:block">
          <p class="text-sm font-semibold text-[var(--text)]">Helios</p>
          <p class="text-xs text-[var(--text-muted)]">Irrigation prototype</p>
        </div>
      </div>
      <nav class="flex-1 px-3 py-5">
        <ul class="space-y-1">
          ${NAV_ITEMS.map(
            (item) => `
              <li>
                <button
                  type="button"
                  data-nav="${item.id}"
                  class="${classNames(
                    "group flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium transition-all duration-200",
                    state.activePage === item.id
                      ? "bg-[var(--accent-soft)] text-[var(--text)]"
                      : "text-[var(--text-muted)] hover:bg-[var(--panel-hover)] hover:text-[var(--text)]",
                  )}"
                >
                  <span class="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--panel)]">
                    ${icon(item.icon)}
                  </span>
                  <span class="hidden xl:block">${item.label}</span>
                </button>
              </li>
            `,
          ).join("")}
        </ul>
      </nav>
      <div class="border-t border-[var(--border)] px-3 py-4">
        <div class="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--panel)] px-3 py-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            ${icon("user")}
          </div>
          <div class="hidden xl:block">
            <p class="text-sm font-medium">Field Ops</p>
            <p class="text-xs text-[var(--text-muted)]">Prototype tenant</p>
          </div>
        </div>
      </div>
    </aside>
  `;
}

function TopBar() {
  return `
    <header class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--border)] bg-[var(--bg)] px-4 backdrop-blur sm:px-6">
      <div>
        <h1 class="text-[22px] font-semibold tracking-tight">${PAGE_TITLES[state.activePage]}</h1>
      </div>
      <div class="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          id="theme-toggle"
          class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
          aria-label="Toggle theme"
        >
          ${icon(state.theme === "dark" ? "sun" : "moon")}
        </button>
        <a
          href="https://github.com/marco-trotta1/heliosv2"
          target="_blank"
          rel="noreferrer"
          class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
          aria-label="Open GitHub"
        >
          ${icon("github")}
        </a>
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)]">
          ${icon("user")}
        </div>
      </div>
    </header>
  `;
}

function renderPage() {
  if (state.activePage === "dashboard") {
    return DashboardPage();
  }
  if (state.activePage === "history") {
    return HistoryPage(state.runHistory, "All analysis runs");
  }
  if (state.activePage === "saved") {
    return HistoryPage(state.savedRuns, "Pinned runs and reusable scenarios");
  }
  if (state.activePage === "settings") {
    return SettingsPage();
  }
  return AnalysisWorkspace();
}

function statCard(title, value, hint, iconName) {
  return `
    <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--accent)]">
      <div class="mb-4 flex items-start justify-between">
        <div>
          <p class="text-sm font-medium text-[var(--text-muted)]">${title}</p>
          <p class="mt-3 text-3xl font-semibold tracking-tight text-[var(--text)]">${value}</p>
        </div>
        <span class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
          ${icon(iconName)}
        </span>
      </div>
      <p class="text-sm text-[var(--text-muted)]">${hint}</p>
    </div>
  `;
}

function DashboardPage() {
  const totalRuns = state.runHistory.length;
  const savedRuns = state.savedRuns.length;
  const recentRuns = Math.min(5, totalRuns);
  const latestSummary = state.latestRun ? state.latestRun.summary : "No recent analyses yet.";
  return `
    <section class="space-y-6">
      <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.2em] text-[var(--text-muted)]">Overview</p>
        <div class="mt-4 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div class="max-w-3xl">
            <h2 class="text-2xl font-semibold tracking-tight text-[var(--text)]">Field operations cockpit</h2>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
              Helios combines soil signals, weather pressure, and farm constraints into a single operator dashboard.
              Review recent runs, jump into analysis mode, and reuse saved scenarios without changing the underlying irrigation logic.
            </p>
          </div>
          <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-sm text-[var(--text-muted)]">
            Latest note: <span class="text-[var(--text)]">${escapeHtml(latestSummary)}</span>
          </div>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        ${statCard("Recent Runs", recentRuns, "Analyses captured in the most recent working set.", "history")}
        ${statCard("Saved Analyses", savedRuns, "Pinned scenarios ready for repeat review.", "bookmark")}
        ${statCard("Total Runs", totalRuns, "Cumulative analyses stored in local browser history.", "chart")}
      </div>

      <div class="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <div class="mb-4 flex items-center justify-between">
            <div>
              <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recent Activity</p>
              <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Last analyses</h3>
            </div>
            <button
              type="button"
              data-nav="run-analysis"
              class="inline-flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              ${icon("sparkles", "h-4 w-4")}
              <span>New analysis</span>
            </button>
          </div>
          <div class="space-y-3">
            ${state.runHistory.slice(0, 4).map((run) => dashboardRunItem(run)).join("") || emptyBlock("No runs yet", "Start with Run Analysis to populate the dashboard feed.")}
          </div>
        </div>
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Saved Templates</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Quick launch presets</h3>
          <div class="mt-5 space-y-3">
            ${Object.entries(PRESETS)
              .map(
                ([key, preset]) => `
                  <button
                    type="button"
                    data-preset="${key}"
                    class="flex w-full items-start justify-between rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-left transition-all duration-200 hover:border-[var(--accent)] hover:bg-[var(--panel-hover)]"
                  >
                    <div>
                      <p class="text-sm font-medium text-[var(--text)]">${escapeHtml(preset.fieldName)}</p>
                      <p class="mt-1 text-sm text-[var(--text-muted)]">${escapeHtml(preset.analysisPrompt)}</p>
                    </div>
                    <span class="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                      ${icon("sparkles", "h-4 w-4")}
                    </span>
                  </button>
                `,
              )
              .join("")}
          </div>
        </div>
      </div>
    </section>
  `;
}

function dashboardRunItem(run) {
  return `
    <article class="fade-in rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-sm font-medium text-[var(--text)]">${escapeHtml(run.inputSnapshot.fieldName)}</p>
          <p class="mt-1 text-sm text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="text-right">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
          <p class="mt-2 text-sm font-medium ${run.decision === "water" ? "text-[var(--warning)]" : "text-[var(--success)]"}">${run.decision.toUpperCase()}</p>
        </div>
      </div>
    </article>
  `;
}

function emptyBlock(title, body) {
  return `
    <div class="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--panel-muted)] px-5 py-10 text-center">
      <p class="text-sm font-medium text-[var(--text)]">${title}</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">${body}</p>
    </div>
  `;
}

function PrimaryButton({ id = "", label, iconName = "", variant = "primary", extraClass = "", type = "button", disabled = false }) {
  const palette =
    variant === "primary"
      ? "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
      : "border border-[var(--border)] bg-[var(--panel-muted)] text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)]";
  return `
    <button
      ${id ? `id="${id}"` : ""}
      type="${type}"
      ${disabled ? "disabled" : ""}
      class="${classNames(
        "inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-200",
        disabled ? "cursor-not-allowed opacity-60" : "",
        palette,
        extraClass,
      )}"
    >
      ${iconName ? icon(iconName, "h-4 w-4") : ""}
      <span>${label}</span>
    </button>
  `;
}

function PromptInput() {
  const modeLabel =
    state.analysis.source === "api"
      ? "Live API mode"
      : state.analysis.source === "local"
        ? "Fallback mode"
        : "Demo mode";
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Prompt</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-[var(--text)]">Describe the field situation and what you need to decide</h2>
          <p class="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">
            Start here. Enter the request in plain language, then review the recommendation below before checking supporting data.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <div class="hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)] sm:block">
            ${modeLabel}
          </div>
          ${Object.keys(PRESETS)
            .map((key) => PrimaryButton({ label: key === "heatwave" ? "Heat wave" : key === "balanced" ? "Balanced day" : "Rain incoming", iconName: "sparkles", variant: "secondary", extraClass: "preset-trigger", id: "", type: "button" }).replace("<button", `<button data-preset="${key}"`))
            .join("")}
        </div>
      </div>
      <textarea
        id="analysis-prompt"
        name="analysisPrompt"
        rows="4"
        class="mt-5 w-full rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-sm leading-7 text-[var(--text)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
        placeholder="Enter your request, scenario, or irrigation question here..."
      >${escapeHtml(state.form.analysisPrompt)}</textarea>
      <div class="mt-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div class="flex flex-1 flex-col gap-4">
          <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-sm text-[var(--text-muted)]">
            <p>${escapeHtml(state.analysis.status)}</p>
            ${state.analysis.error ? `<p class="mt-2 text-[var(--accent-warm)]">${escapeHtml(state.analysis.error)}</p>` : ""}
            <p class="mt-2">Prototype note: synthetic training data, approximate ET, heuristic confidence, and rule-based optimization.</p>
          </div>
          <div class="flex flex-1 flex-col gap-3 xl:flex-row xl:items-center">
          <label class="text-sm text-[var(--text-muted)]">
            <span class="mb-2 block text-sm font-medium text-[var(--text-muted)]">Model</span>
            <select
              name="model"
              class="min-w-[180px] rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
            >
              ${["Helios Core", "Helios Balanced", "Helios Conservative"]
                .map((option) => `<option value="${option}" ${state.form.model === option ? "selected" : ""}>${option}</option>`)
                .join("")}
            </select>
          </label>
          <div class="flex flex-wrap items-center gap-3 pt-1">
            ${toggleControl("autoSave", "Auto-save run", state.form.autoSave)}
            ${toggleControl("includeNotes", "Detailed notes", state.form.includeNotes)}
          </div>
        </div>
        </div>
        <div class="flex justify-start xl:justify-end">
          ${PrimaryButton({
          id: "run-analysis-button",
          label: state.analysis.submitting ? "Running..." : "Run analysis",
          iconName: "sparkles",
          variant: "primary",
          type: "submit",
          extraClass: "min-w-[160px]",
          disabled: state.analysis.submitting,
        })}
        </div>
      </div>
    </section>
  `;
}

function toggleControl(name, label, checked) {
  return `
    <label class="inline-flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm text-[var(--text)]">
      <input
        type="checkbox"
        name="${name}"
        ${checked ? "checked" : ""}
        class="h-4 w-4 rounded border-[var(--border)] bg-transparent text-[var(--accent)] focus:ring-[var(--accent)]"
      />
      <span>${label}</span>
    </label>
  `;
}

function fieldCard(title, description, content) {
  return `
    <section class="rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
      <div class="mb-5">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${title}</p>
        <h3 class="mt-2 text-base font-medium text-[var(--text)]">${description}</h3>
      </div>
      ${content}
    </section>
  `;
}

function inputGroup(label, control) {
  return `
    <label class="block">
      <span class="mb-2 block text-sm font-medium text-[var(--text-muted)]">${label}</span>
      ${control}
    </label>
  `;
}

function numericInput(name, value, min, step = "0.1", max = "") {
  return `
    <input
      name="${name}"
      type="number"
      value="${value}"
      min="${min}"
      ${max !== "" ? `max="${max}"` : ""}
      step="${step}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    />
  `;
}

function textInput(name, value) {
  return `
    <input
      name="${name}"
      type="text"
      value="${escapeHtml(value)}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    />
  `;
}

function selectInput(name, value, options) {
  return `
    <select
      name="${name}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    >
      ${options
        .map((option) => `<option value="${option.value}" ${value === option.value ? "selected" : ""}>${option.label}</option>`)
        .join("")}
    </select>
  `;
}

function checkboxGroup(title, name, options, selected) {
  return `
    <fieldset class="rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] p-4">
      <legend class="px-1 text-sm font-medium text-[var(--text-muted)]">${title}</legend>
      <div class="mt-3 grid gap-3">
        ${options
          .map(
            (option) => `
              <label class="inline-flex items-center gap-3 text-sm text-[var(--text)]">
                <input
                  type="checkbox"
                  name="${name}"
                  value="${option.value}"
                  ${selected.includes(option.value) ? "checked" : ""}
                  class="h-4 w-4 rounded border-[var(--border)] bg-transparent text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <span>${option.label}</span>
              </label>
            `,
          )
          .join("")}
      </div>
    </fieldset>
  `;
}

function FieldProfileSection() {
  return fieldCard(
    "Field Profile",
    "Crop, soil, and terrain descriptors",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Field name", textInput("fieldName", state.form.fieldName))}
      ${inputGroup("Farm ID", textInput("farmId", state.form.farmId))}
      ${inputGroup("Field area (ha)", numericInput("fieldAreaHa", state.form.fieldAreaHa, "1"))}
      ${inputGroup("Latitude", numericInput("locationLat", state.form.locationLat, "-90", "0.0001", "90"))}
      ${inputGroup("Longitude", numericInput("locationLon", state.form.locationLon, "-180", "0.0001", "180"))}
      ${inputGroup("Crop type", selectInput("cropType", state.form.cropType, [
        { value: "corn", label: "Corn" },
        { value: "soybean", label: "Soybean" },
        { value: "potato", label: "Potato" },
        { value: "alfalfa", label: "Alfalfa" },
        { value: "wheat", label: "Wheat" },
      ]))}
      ${inputGroup("Growth stage", selectInput("growthStage", state.form.growthStage, [
        { value: "emergence", label: "Emergence" },
        { value: "vegetative", label: "Vegetative" },
        { value: "flowering", label: "Flowering" },
        { value: "grain_fill", label: "Grain fill" },
        { value: "maturity", label: "Maturity" },
      ]))}
      ${inputGroup("Soil texture", selectInput("soilTexture", state.form.soilTexture, [
        { value: "sand", label: "Sand" },
        { value: "loam", label: "Loam" },
        { value: "clay", label: "Clay" },
      ]))}
      ${inputGroup("Drainage", selectInput("drainageClass", state.form.drainageClass, [
        { value: "poor", label: "Poor" },
        { value: "moderate", label: "Moderate" },
        { value: "well", label: "Well drained" },
      ]))}
      ${inputGroup("Infiltration rate (mm/hr)", numericInput("infiltrationRate", state.form.infiltrationRate, "1"))}
      ${inputGroup("Slope (%)", numericInput("slopePct", state.form.slopePct, "0"))}
    </div>`,
  );
}

function SensorFeedSection() {
  return fieldCard(
    "Sensor Feed",
    "Soil moisture and weather inputs",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Current soil moisture", numericInput("currentMoisture", state.form.currentMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("6h ago moisture", numericInput("lagOneMoisture", state.form.lagOneMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("12h ago moisture", numericInput("lagTwoMoisture", state.form.lagTwoMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("Temperature (C)", numericInput("temperatureC", state.form.temperatureC, "-5"))}
      ${inputGroup("Humidity (%)", numericInput("humidityPct", state.form.humidityPct, "0", "1", "100"))}
      ${inputGroup("Wind (m/s)", numericInput("windMps", state.form.windMps, "0"))}
      ${inputGroup("Forecast precipitation (mm)", numericInput("precipitationMm", state.form.precipitationMm, "0"))}
      ${inputGroup("Solar radiation (MJ/m²)", numericInput("solarRadiationMjM2", state.form.solarRadiationMjM2, "0"))}
    </div>`,
  );
}

function OperationsSection() {
  return fieldCard(
    "Operations",
    "System constraints and scheduling rules",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Irrigation type", selectInput("irrigationType", state.form.irrigationType, [
        { value: "pivot", label: "Pivot" },
        { value: "drip", label: "Drip" },
        { value: "flood", label: "Flood" },
      ]))}
      ${inputGroup("Pump capacity (mm/hr)", numericInput("pumpCapacity", state.form.pumpCapacity, "0.5"))}
      ${inputGroup("Max irrigation volume (mm)", numericInput("maxIrrigationVolume", state.form.maxIrrigationVolume, "0"))}
      ${inputGroup("Budget ($)", numericInput("budgetDollars", state.form.budgetDollars, "0", "1"))}
      ${inputGroup("Irrigation last 24h (mm)", numericInput("recentIrrigation24h", state.form.recentIrrigation24h, "0"))}
      ${inputGroup("Irrigation last 72h (mm)", numericInput("recentIrrigation72h", state.form.recentIrrigation72h, "0"))}
    </div>
    <div class="mt-5 grid gap-4">
      ${checkboxGroup("Water rights schedule", "waterWindow", [
        { value: "tonight", label: "Tonight" },
        { value: "tomorrow_morning", label: "Tomorrow morning" },
        { value: "tomorrow_afternoon", label: "Tomorrow afternoon" },
        { value: "tomorrow_night", label: "Tomorrow night" },
      ], state.form.waterWindow)}
      ${checkboxGroup("Lower-cost energy windows", "energyWindow", [
        { value: "tonight", label: "Tonight" },
        { value: "tomorrow_morning", label: "Tomorrow morning" },
        { value: "tomorrow_afternoon", label: "Tomorrow afternoon" },
        { value: "tomorrow_night", label: "Tomorrow night" },
      ], state.form.energyWindow)}
    </div>`,
  );
}

function DataSection() {
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="max-w-3xl">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Data</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-[var(--text)]">Supporting field context</h2>
        <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
          Review or update the field details that support the recommendation. These inputs stay grouped together so they inform the decision without competing with it.
        </p>
      </div>
      <div class="mt-6 grid gap-4 xl:grid-cols-3">
        ${FieldProfileSection()}
        ${SensorFeedSection()}
        ${OperationsSection()}
      </div>
    </section>
  `;
}

function AnalysisConsoleDisclosure() {
  const expanded = state.analysisConsoleOpen;
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-3 shadow-[var(--shadow)]">
      <button
        type="button"
        id="analysis-console-toggle"
        aria-expanded="${expanded ? "true" : "false"}"
        aria-controls="analysis-console-panel"
        class="flex w-full items-center justify-between gap-4 rounded-[22px] px-3 py-3 text-left transition-all duration-200 hover:bg-[var(--panel-muted)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <div>
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Analysis Console</p>
          <p class="mt-2 text-sm text-[var(--text-muted)]">
            Open recent runs, copyable analysis details, and technical output when you need deeper review.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <span class="hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)] sm:inline-flex">
            ${state.runHistory.length} stored
          </span>
          <span class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] text-[var(--text-muted)]">
            <span class="transition-transform duration-200 ${expanded ? "rotate-180" : ""}">
              ${icon("chevronDown", "h-5 w-5")}
            </span>
          </span>
        </div>
      </button>
      <div
        id="analysis-console-panel"
        aria-hidden="${expanded ? "false" : "true"}"
        ${expanded ? "" : "inert"}
        class="${classNames(
          "grid overflow-hidden transition-all duration-300 ease-out",
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}"
      >
        <div class="min-h-0">
          <div class="border-t border-[var(--border)] px-3 pb-3 pt-4">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="text-lg font-medium text-[var(--text)]">Recent analysis runs</h2>
                <p class="mt-1 text-sm text-[var(--text-muted)]">Technical details stay available here without interrupting the main decision flow.</p>
              </div>
              <div class="flex items-center gap-2">
                ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
                <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)]">
                  ${state.runHistory.length} total
                </div>
              </div>
            </div>
            <div class="mt-4 space-y-3">
              ${state.runHistory.length > 0
                ? state.runHistory.slice(0, 8).map((run) => ResultCard(run, true)).join("")
                : emptyInspectorState()}
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function AnalysisWorkspace() {
  return `
    <section class="space-y-6">
      <form id="analysis-form" class="space-y-6">
        ${PromptInput()}
        ${RecommendationSpotlight()}
        ${DataSection()}
        ${AnalysisConsoleDisclosure()}
      </form>
    </section>
  `;
}

function RecommendationSpotlight() {
  if (!state.latestRun) {
    return `
      <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation</p>
            <h3 class="mt-2 text-xl font-semibold text-[var(--text)]">Run an analysis to reveal the irrigation call</h3>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
              The result will surface here with the recommended amount, timing window, heuristic confidence, and the main drivers behind the estimate.
            </p>
          </div>
          <span class="hidden rounded-full bg-[var(--accent-soft)] px-4 py-2 text-xs font-medium text-[var(--accent)] lg:inline-flex">
            Waiting for first run
          </span>
        </div>
      </section>
    `;
  }

  const run = state.latestRun;
  const tone = recommendationTone(run);
  return `
    <section class="accent-divider rounded-[28px] border p-6 shadow-[var(--shadow)] ${tone.spotlight}">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="max-w-2xl">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation</p>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <h3 class="text-[28px] font-semibold tracking-tight text-[var(--text)]">${run.decision === "water" ? "Irrigate now" : "Hold irrigation"}</h3>
            <span class="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${tone.pill}">
              ${run.decision.toUpperCase()}
            </span>
          </div>
          <p class="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-right">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Latest run</p>
          <p class="mt-2 text-sm font-medium text-[var(--text)]">${formatTimestamp(run.timestamp)}</p>
        </div>
      </div>
      <div class="mt-6 grid gap-4 lg:grid-cols-[1.2fr_repeat(3,minmax(0,1fr))]">
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommended amount</p>
          <div class="mt-3 flex items-end gap-3">
            <span class="text-5xl font-semibold tracking-tight ${tone.amount}">${run.recommendedAmountMm.toFixed(1)}</span>
            <span class="pb-1 text-lg font-medium text-[var(--text-muted)]">mm</span>
          </div>
          <p class="mt-4 text-sm text-[var(--text-muted)]">This is the number the operator should notice first.</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Best timing</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${escapeHtml(formatWindow(run.timingWindow))}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Heuristic confidence</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${formatPercent(run.confidenceScore)}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Stress risk</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${formatPercent(run.stressProbability)}</p>
        </div>
      </div>
      <div class="mt-4 rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Farmer feedback</p>
            <p class="mt-2 text-sm text-[var(--text-muted)]">${escapeHtml(feedbackSummary(run))}</p>
            ${run.sourceLabel ? `<p class="mt-2 text-sm text-[var(--text-muted)]">Source: ${escapeHtml(run.sourceLabel)}</p>` : ""}
            ${run.recommendationAdjustment ? `<p class="mt-2 text-sm text-[var(--text-muted)]">Adjustment reason: ${escapeHtml(run.recommendationAdjustment.reason)}</p>` : ""}
          </div>
          <button
            type="button"
            id="feedback-toggle"
            ${isLiveApiMode() ? "" : "disabled"}
            class="${classNames(
              "inline-flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200",
              isLiveApiMode() ? "hover:border-[var(--accent)]" : "cursor-not-allowed opacity-60",
            )}"
          >
            ${isLiveApiMode() ? "Submit Feedback" : "Live API required"}
          </button>
        </div>
        ${state.feedbackForm.open ? `
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            ${inputGroup("Did this recommendation work?", selectInput("feedbackOutcome", state.feedbackForm.outcome, [
              { value: "SUCCESS", label: "Success" },
              { value: "PARTIAL", label: "Partial" },
              { value: "FAILURE", label: "Failure" },
            ]))}
            ${inputGroup("Yield change (%)", numericInput("feedbackYieldDelta", state.feedbackForm.yieldDelta, "-100", "0.1", "1000"))}
          </div>
          <div class="mt-4">
            ${inputGroup("Notes", `<textarea id="feedback-notes" class="min-h-[96px] w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]">${escapeHtml(state.feedbackForm.notes)}</textarea>`)}
          </div>
          <div class="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              id="feedback-submit"
              class="inline-flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)]"
            >
              ${state.feedbackForm.submitting ? "Submitting..." : "Send"}
            </button>
            ${state.feedbackForm.error ? `<p class="text-sm text-[var(--accent-warm)]">${escapeHtml(state.feedbackForm.error)}</p>` : ""}
            ${state.feedbackForm.status ? `<p class="text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
          </div>
        ` : state.feedbackForm.status ? `<p class="mt-4 text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
      </div>
    </section>
  `;
}

function HistoryPage(items, subtitle) {
  return `
    <section class="space-y-6">
      <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${PAGE_TITLES[state.activePage]}</p>
        <h2 class="mt-3 text-2xl font-semibold tracking-tight text-[var(--text)]">${subtitle}</h2>
      </div>
      <div class="space-y-3">
        ${items.length > 0 ? items.map((run) => ResultCard(run)).join("") : emptyBlock("No records yet", "Run an analysis to populate this page.")}
      </div>
    </section>
  `;
}

function SettingsPage() {
  return `
    <section class="space-y-6">
      <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Settings</p>
        <h2 class="mt-3 text-2xl font-semibold tracking-tight text-[var(--text)]">Workspace preferences</h2>
      </div>
      <div class="grid gap-6 xl:grid-cols-2">
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Theme</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Current theme</h3>
          <p class="mt-3 text-sm text-[var(--text-muted)]">
            Switch between the default dark operating mode and a light workspace for review sessions.
          </p>
          <div class="mt-5">
            ${PrimaryButton({ id: "theme-toggle-inline", label: state.theme === "dark" ? "Switch to light" : "Switch to dark", iconName: state.theme === "dark" ? "sun" : "moon", variant: "secondary" })}
          </div>
        </div>
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Deployment</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Runtime mode</h3>
          <ul class="mt-4 space-y-3 text-sm text-[var(--text-muted)]">
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">Configured mode: ${escapeHtml(runtimeConfig.mode)}</li>
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">API base URL: ${escapeHtml(runtimeConfig.apiBaseUrl || "same-origin or none")}</li>
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">${escapeHtml(runtimeConfig.disclaimer)}</li>
          </ul>
        </div>
      </div>
    </section>
  `;
}

function ResultsPanel() {
  return `
    <aside class="col-span-2 border-t border-[var(--border)] bg-[var(--bg)] xl:col-span-1 xl:border-l xl:border-t-0">
      <div class="sticky top-0 flex h-full max-h-screen flex-col">
        <div class="flex h-16 items-center justify-between border-b border-[var(--border)] px-4">
          <div>
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Results</p>
            <h2 class="mt-1 text-base font-medium text-[var(--text)]">Analysis console</h2>
          </div>
          <div class="flex items-center gap-2">
            ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
            <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-xs text-[var(--text-muted)]">
              ${state.runHistory.length} total
            </div>
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <div class="space-y-3">
            ${state.runHistory.length > 0
              ? state.runHistory.slice(0, 8).map((run) => ResultCard(run, true)).join("")
              : emptyInspectorState()}
          </div>
        </div>
      </div>
    </aside>
  `;
}

function emptyInspectorState() {
  return `
    <div class="rounded-[28px] border border-dashed border-[var(--border)] bg-[var(--panel)] px-6 py-12 text-center">
      <p class="text-sm font-medium text-[var(--text)]">No analysis yet. Run a prompt to generate results.</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">Results will appear here as reusable cards with copy actions and timestamps.</p>
    </div>
  `;
}

function ResultCard(run, inspectorMode = false) {
  const tone = recommendationTone(run);
  return `
    <article class="fade-in rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-4 shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--accent)]">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h3 class="truncate text-sm font-medium text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "Untitled field")}</h3>
          <p class="mt-1 text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
        </div>
        <button
          type="button"
          data-copy="${run.id}"
          class="inline-flex items-center gap-1 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs font-medium text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
        >
          ${icon("copy", "h-4 w-4")}
          <span>Copy</span>
        </button>
      </div>
      <div class="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] p-4">
          <p class="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation amount</p>
          <div class="mt-2 flex items-end gap-2">
            <span class="text-3xl font-semibold tracking-tight ${tone.amount}">${run.recommendedAmountMm.toFixed(1)}</span>
            <span class="pb-1 text-sm font-medium text-[var(--text-muted)]">mm</span>
          </div>
        </div>
        <div class="flex flex-wrap content-start gap-2">
          <span class="rounded-full px-3 py-1 text-xs font-medium ${tone.pill}">${run.decision.toUpperCase()}</span>
          <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">${formatWindow(run.timingWindow)}</span>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">Heuristic confidence ${formatPercent(run.confidenceScore)}</span>
        <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">Stress ${formatPercent(run.stressProbability)}</span>
      </div>
      ${inspectorMode ? `<div class="mt-4 h-px bg-[var(--border)]"></div>` : ""}
      <pre class="mt-4 overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] p-4 font-mono text-[12px] leading-6 text-[var(--text-muted)]">${escapeHtml(run.copyText)}</pre>
    </article>
  `;
}

function bindAppEvents() {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.nav));
  });

  document.querySelector("#theme-toggle")?.addEventListener("click", toggleTheme);
  document.querySelector("#theme-toggle-inline")?.addEventListener("click", toggleTheme);

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => applyPreset(button.dataset.preset));
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => {
      const run = [...state.runHistory, ...state.savedRuns].find((item) => item.id === button.dataset.copy);
      if (run) {
        copyText(run.copyText, button);
      }
    });
  });

  const form = document.querySelector("#analysis-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      syncFormState(form);
      evaluateScenario();
    });

    form.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target instanceof HTMLInputElement && target.type === "checkbox") {
        if (target.name === "waterWindow" || target.name === "energyWindow") {
          updateArrayField(target.name, target.value, target.checked);
        } else {
          updateFormField(target.name, target.checked);
        }
      } else if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement) {
        updateFormField(target.name, parseFieldValue(target));
      }

      if (target instanceof HTMLTextAreaElement) {
        autoSizeTextarea(target);
      }
    });
  }

  document.querySelector("#save-latest-run")?.addEventListener("click", saveLatestRun);
  document.querySelector("#analysis-console-toggle")?.addEventListener("click", () => {
    state.analysisConsoleOpen = !state.analysisConsoleOpen;
    renderApp();
  });
  document.querySelector("#feedback-toggle")?.addEventListener("click", () => {
    state.feedbackForm.open = !state.feedbackForm.open;
    state.feedbackForm.error = "";
    renderApp();
  });
  document.querySelector("#feedback-submit")?.addEventListener("click", submitFeedback);
  document.querySelector('select[name="feedbackOutcome"]')?.addEventListener("input", (event) => {
    state.feedbackForm.outcome = event.target.value;
  });
  document.querySelector('input[name="feedbackYieldDelta"]')?.addEventListener("input", (event) => {
    state.feedbackForm.yieldDelta = event.target.value;
  });
  document.querySelector("#feedback-notes")?.addEventListener("input", (event) => {
    state.feedbackForm.notes = event.target.value;
    autoSizeTextarea(event.target);
  });
}

function parseFieldValue(target) {
  if (target.type === "number") {
    return Number(target.value);
  }
  return target.value;
}

function syncFormState(form) {
  const formData = new FormData(form);
  for (const [key, value] of formData.entries()) {
    if (key === "waterWindow" || key === "energyWindow") {
      continue;
    }
    const field = form.elements.namedItem(key);
    if (field instanceof HTMLInputElement && field.type === "checkbox") {
      state.form[key] = field.checked;
    } else if (field instanceof HTMLInputElement && field.type === "number") {
      state.form[key] = Number(value);
    } else {
      state.form[key] = value;
    }
  }
  state.form.waterWindow = [...form.querySelectorAll('input[name="waterWindow"]:checked')].map((item) => item.value);
  state.form.energyWindow = [...form.querySelectorAll('input[name="energyWindow"]:checked')].map((item) => item.value);
}

function autoSizeTextarea(textarea) {
  textarea.style.height = "0px";
  textarea.style.height = `${textarea.scrollHeight}px`;
}

function resizePromptInput() {
  const prompt = document.querySelector("#analysis-prompt");
  if (prompt) {
    autoSizeTextarea(prompt);
  }
}
