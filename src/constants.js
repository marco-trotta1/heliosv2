export const SOIL_THRESHOLDS = {
  sand: { dry: 0.12, wet: 0.28 },
  loam: { dry: 0.18, wet: 0.35 },
  clay: { dry: 0.22, wet: 0.4 },
};

export const ROOT_ZONE_FACTORS = {
  sand: 110,
  loam: 135,
  clay: 155,
};

export const IRRIGATION_EFFICIENCY = {
  pivot: 0.82,
  drip: 0.93,
  flood: 0.68,
};

export const GROWTH_STAGE_MODIFIER = {
  emergence: 0.05,
  vegetative: 0.1,
  flowering: 0.18,
  grain_fill: 0.14,
  maturity: 0.02,
};

export const TEXTURE_RETENTION = {
  sand: 0.91,
  loam: 1,
  clay: 1.08,
};

export const DRAINAGE_FACTOR = {
  poor: 0.88,
  moderate: 1,
  well: 1.12,
};

export const PAGE_TITLES = {
  dashboard: "Dashboard",
  "run-analysis": "Run Analysis",
  history: "History",
  saved: "Saved Runs",
  settings: "Settings",
};

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "layout" },
  { id: "run-analysis", label: "Run Analysis", icon: "sparkles" },
  { id: "history", label: "History", icon: "history" },
  { id: "saved", label: "Saved Runs", icon: "bookmark" },
  { id: "settings", label: "Settings", icon: "settings" },
];

export const RUN_HISTORY_KEY = "helios-pages-history";
export const SAVED_RUNS_KEY = "helios-pages-saved-runs";
export const THEME_KEY = "helios-dashboard-theme";

export const BRAND_LOGOS = {
  dark: "assets/irrigant-dark.svg",
  light: "assets/irrigant-light.svg",
};

export const DEFAULT_RUNTIME_CONFIG = {
  mode: "demo",
  apiBaseUrl: "",
  disclaimer:
    "Demo mode uses browser-side prototype logic only. It does not call a live backend or store feedback in the project database.",
};

export const DEFAULT_FORM = {
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

export const PRESETS = {
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
