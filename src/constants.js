export const SOIL_THRESHOLDS = {
  sand: { dry: 0.12, wet: 0.28 },
  loam: { dry: 0.18, wet: 0.35 },
  clay: { dry: 0.22, wet: 0.4 },
};

export const ROOT_ZONE_FACTORS = {
  sand: 4.331,  // inches (was 110 mm)
  loam: 5.315,  // inches (was 135 mm)
  clay: 6.102,  // inches (was 155 mm)
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

export const INFILTRATION_RATE_BY_TEXTURE = {
  sand: 1.00,   // in/hr — coarse, fast-draining
  loam: 0.47,   // in/hr — typical (matches default)
  clay: 0.20,   // in/hr — fine-grained, slow
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
  fieldAreaAcres: 59.3,         // was 24 ha
  cropType: "corn",
  growthStage: "flowering",
  soilTexture: "loam",
  drainageClass: "moderate",
  infiltrationRate: 0.47,       // in/hr (was 12 mm/hr)
  slopePct: 2.5,
  locationLat: 43.615,
  locationLon: -116.202,
  currentMoisture: 0.2,
  lagOneMoisture: 0.21,
  lagTwoMoisture: 0.22,
  temperatureF: 87.8,           // was 31 °C
  humidityPct: 38,
  windMph: 8.5,                 // was 3.8 m/s
  precipitationIn: 0,           // was 0 mm
  solarRadiationMjM2: 24,
  irrigationType: "pivot",
  pumpCapacity: 0.24,           // in/hr (was 6 mm/hr)
  maxIrrigationVolume: 0.71,    // in (was 18 mm)
  budgetDollars: 2800,
  recentIrrigation24h: 0.31,    // in (was 8 mm)
  recentIrrigation72h: 0.47,    // in (was 12 mm)
  waterWindow: ["tonight", "tomorrow_morning"],
  energyWindow: ["tonight", "tomorrow_night"],
  modelRmse: 0.12,
  sensorCount: 1,
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
    temperatureF: 93.2,         // was 34 °C
    humidityPct: 26,
    windMph: 10.3,              // was 4.6 m/s
    precipitationIn: 0,
    solarRadiationMjM2: 28,
    currentMoisture: 0.2,
    lagOneMoisture: 0.21,
    lagTwoMoisture: 0.22,
    recentIrrigation24h: 0.24,  // in (was 6 mm)
    recentIrrigation72h: 0.39,  // in (was 10 mm)
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
    fieldAreaAcres: 44.5,       // was 18 ha
    cropType: "soybean",
    growthStage: "vegetative",
    irrigationType: "drip",
    currentMoisture: 0.27,
    lagOneMoisture: 0.275,
    lagTwoMoisture: 0.278,
    temperatureF: 80.6,         // was 27 °C
    humidityPct: 52,
    windMph: 6.3,               // was 2.8 m/s
    precipitationIn: 0.11,      // was 2.8 mm
    solarRadiationMjM2: 21,
    pumpCapacity: 0.18,         // in/hr (was 4.5 mm/hr)
    maxIrrigationVolume: 0.47,  // in (was 12 mm)
    budgetDollars: 2200,
    recentIrrigation24h: 0.08,  // in (was 2 mm)
    recentIrrigation72h: 0.20,  // in (was 5 mm)
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
    fieldAreaAcres: 76.6,       // was 31 ha
    cropType: "potato",
    growthStage: "grain_fill",
    soilTexture: "clay",
    drainageClass: "poor",
    infiltrationRate: 0.28,     // in/hr (was 7 mm/hr)
    slopePct: 1.2,
    currentMoisture: 0.31,
    lagOneMoisture: 0.305,
    lagTwoMoisture: 0.298,
    temperatureF: 73.4,         // was 23 °C
    humidityPct: 66,
    windMph: 4.9,               // was 2.2 m/s
    precipitationIn: 0.43,      // was 11 mm
    solarRadiationMjM2: 16,
    pumpCapacity: 0.23,         // in/hr (was 5.8 mm/hr)
    maxIrrigationVolume: 0.63,  // in (was 16 mm)
    budgetDollars: 3200,
    recentIrrigation24h: 0,
    recentIrrigation72h: 0.16,  // in (was 4 mm)
    waterWindow: ["tonight", "tomorrow_night"],
    energyWindow: ["tomorrow_night"],
  },
};
