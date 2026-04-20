import { PRESETS } from "../constants.js";
import { isLiveApiMode, state } from "../state.js";
import {
  PrimaryButton,
  autoWeatherTag,
  checkboxGroup,
  escapeHtml,
  fieldCard,
  inputGroup,
  numericInput,
  selectInput,
  textInput,
  toggleControl,
} from "./shared.js";

const PROMPT_TEXTAREA_CLASSES = [
  "focus-outline",
  "min-h-[230px]",
  "w-full",
  "rounded-[28px]",
  "border",
  "border-[var(--border)]",
  "bg-[var(--panel)]",
  "px-5",
  "py-4",
  "text-[15px]",
  "leading-8",
  "text-[var(--text)]",
  "outline-none",
  "transition-all",
  "duration-200",
  "focus:border-[var(--accent)]",
  "focus:bg-[var(--panel)]",
  "shadow-[var(--shadow)]",
].join(" ");

function FieldProfileSection() {
  return fieldCard(
    "Field Profile",
    "Field basics and crop context",
    `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Field name", textInput("fieldName", state.form.fieldName), "", "Name used in run history and saved scenarios.")}
      ${inputGroup("Farm ID", textInput("farmId", state.form.farmId), "", "Internal field identifier for this location.")}
      ${inputGroup("Field area (ac)", numericInput("fieldAreaAcres", state.form.fieldAreaAcres, "1"), "", "Acres covered by this irrigation recommendation.")}
      ${inputGroup("Crop type", selectInput("cropType", state.form.cropType, [
        { value: "corn", label: "Corn" },
        { value: "soybean", label: "Soybean" },
        { value: "potato", label: "Potato" },
        { value: "alfalfa", label: "Alfalfa" },
        { value: "wheat", label: "Wheat" },
      ]), "", "Crop selection keeps thresholds and timing in context.")}
      ${inputGroup("Growth stage", selectInput("growthStage", state.form.growthStage, [
        { value: "emergence", label: "Emergence" },
        { value: "vegetative", label: "Vegetative" },
        { value: "flowering", label: "Flowering" },
        { value: "grain_fill", label: "Grain fill" },
        { value: "maturity", label: "Maturity" },
      ]), "", "Growth stage influences water sensitivity.")}
      ${inputGroup("Soil texture", selectInput("soilTexture", state.form.soilTexture, [
        { value: "sand", label: "Sand" },
        { value: "loam", label: "Loam" },
        { value: "clay", label: "Clay" },
      ]), "", "Used to interpret retention and dry thresholds.")}
      ${inputGroup("Drainage", selectInput("drainageClass", state.form.drainageClass, [
        { value: "poor", label: "Poor" },
        { value: "moderate", label: "Moderate" },
        { value: "well", label: "Well drained" },
      ]), "", "How quickly excess water leaves the profile.")}
      ${inputGroup("Infiltration rate (in/hr)", numericInput("infiltrationRate", state.form.infiltrationRate, "0.01"), "", "Maximum intake rate before runoff becomes more likely.")}
      ${inputGroup("Slope (%)", numericInput("slopePct", state.form.slopePct, "0"), "", "Terrain slope helps estimate drying and runoff pressure.")}
      ${inputGroup("Latitude", numericInput("locationLat", state.form.locationLat, "-90", "0.0001", "90"), "", "Used for weather lookups and regional context.")}
      ${inputGroup("Longitude", numericInput("locationLon", state.form.locationLon, "-180", "0.0001", "180"), "", "Used for weather lookups and regional context.")}
    </div>`,
    "Field and crop setup",
  );
}

function SensorFeedSection() {
  return fieldCard(
    "Current Conditions",
    "Soil moisture and weather readings",
    `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Current soil moisture (0–1 VWC)", numericInput("currentMoisture", state.form.currentMoisture, "0.05", "0.01", "0.6"), "", "Latest volumetric water content from the driest representative zone.")}
      ${inputGroup("Moisture 6h ago (0–1 VWC)", numericInput("lagOneMoisture", state.form.lagOneMoisture, "0.05", "0.01", "0.6"), "", "Recent trend point used to estimate direction of change.")}
      ${inputGroup("Moisture 12h ago (0–1 VWC)", numericInput("lagTwoMoisture", state.form.lagTwoMoisture, "0.05", "0.01", "0.6"), "", "Earlier trend point used to measure how quickly the field is drying.")}
      ${inputGroup("Temperature (°F)", numericInput("temperatureF", state.form.temperatureF, "-58"), autoWeatherTag("temperatureF"), "Live or manual air temperature.")}
      ${inputGroup("Humidity (%)", numericInput("humidityPct", state.form.humidityPct, "0", "1", "100"), autoWeatherTag("humidityPct"), "Relative humidity for current field conditions.")}
      ${inputGroup("Wind (mph)", numericInput("windMph", state.form.windMph, "0"), autoWeatherTag("windMph"), "Wind exposure increases surface drying demand.")}
      ${inputGroup("Forecast precipitation (in)", numericInput("precipitationIn", state.form.precipitationIn, "0"), autoWeatherTag("precipitationIn"), "Expected rainfall in the forecast window.")}
      ${inputGroup("Solar radiation (MJ/m²)", numericInput("solarRadiationMjM2", state.form.solarRadiationMjM2, "0"), autoWeatherTag("solarRadiationMjM2"), "Used to approximate evaporative demand.")}
      ${inputGroup("Soil moisture sensors", numericInput("sensorCount", state.form.sensorCount, "0", "1", "10"), "", "Count of sensors contributing to the reading picture.")}
    </div>`,
    "Moisture and weather feed",
  );
}

function OperationsSection() {
  return fieldCard(
    "Irrigation Setup",
    "System limits and operating windows",
    `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Irrigation type", selectInput("irrigationType", state.form.irrigationType, [
        { value: "pivot", label: "Pivot" },
        { value: "drip", label: "Drip" },
        { value: "flood", label: "Flood" },
      ]), "", "Delivery system used for this field.")}
      ${inputGroup("Pump capacity (in/hr)", numericInput("pumpCapacity", state.form.pumpCapacity, "0.01"), "", "Estimated application throughput during an allowed run.")}
      ${inputGroup("Max irrigation volume (in)", numericInput("maxIrrigationVolume", state.form.maxIrrigationVolume, "0"), "", "Upper bound for a single recommendation.")}
      ${inputGroup("Budget ($)", numericInput("budgetDollars", state.form.budgetDollars, "0", "1"), "", "Daily or near-term operating budget for water and energy.")}
      ${inputGroup("Irrigation last 24h (in)", numericInput("recentIrrigation24h", state.form.recentIrrigation24h, "0"), "", "Water already applied in the last day.")}
      ${inputGroup("Irrigation last 72h (in)", numericInput("recentIrrigation72h", state.form.recentIrrigation72h, "0"), "", "Water already applied across the last three days.")}
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
    "Pumps, budget, and timing",
  );
}

export function DataSection() {
  return `
    <section class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow-strong)] sm:p-7">
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)] xl:items-start">
        <div class="max-w-3xl">
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--accent)]">Supporting Data</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]">Keep the inputs clear, grouped, and easy to scan</h2>
          <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
            Everything Helios already needs is still here. The inputs are simply regrouped so farmers can review field context without losing the main decision.
          </p>
        </div>
        <div class="rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-sm text-[var(--text-muted)]">
          <p class="font-semibold text-[var(--text)]">Farmer-facing reading order</p>
          <p class="mt-2 leading-6">Field Profile establishes the crop and field baseline, Current Conditions covers moisture and weather, and Irrigation Setup captures the operating limits.</p>
        </div>
      </div>
      <div class="mt-6 grid gap-4">
        ${FieldProfileSection()}
        ${SensorFeedSection()}
        ${OperationsSection()}
      </div>
    </section>
  `;
}

function modeLabel() {
  if (!isLiveApiMode()) {
    return "Demo workspace";
  }
  if (state.backend.status === "checking") {
    return "Checking backend";
  }
  if (state.backend.status === "unavailable") {
    return "Backend unavailable";
  }
  const hash = state.backend.modelHash ? state.backend.modelHash.slice(0, 7) : "unknown";
  const trained = state.backend.trainingDate ? state.backend.trainingDate.slice(0, 10) : "unknown date";
  return `Live model ${hash} • trained ${trained}`;
}

export function PromptInput() {
  return `
    <section class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow-strong)] sm:p-7">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(290px,0.75fr)]">
        <div>
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--accent)]">Decision Brief</p>
          <h2 class="mt-2 text-[30px] font-semibold tracking-[-0.04em] text-[var(--text)]">Describe the field situation and the irrigation decision you need to make</h2>
          <p class="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">
            Start with the plain-language question. Helios will surface the recommendation first, then keep the supporting data underneath for review.
          </p>
          <div class="mt-5 flex flex-wrap gap-2.5">
            ${Object.keys(PRESETS)
              .map((key) => {
                const label = key === "heatwave"
                  ? "Heat wave"
                  : key === "balanced"
                    ? "Balanced day"
                    : key === "kimberly"
                      ? "Kimberly Farm"
                      : "Rain incoming";
                return `
                  <button
                    type="button"
                    data-preset="${key}"
                    class="focus-outline inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-2 text-sm font-semibold text-[var(--text)] transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--panel)]"
                  >
                    <span class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">•</span>
                    <span>${label}</span>
                  </button>
                `;
              })
              .join("")}
          </div>
          <textarea
            id="analysis-prompt"
            name="analysisPrompt"
            rows="4"
            class="${PROMPT_TEXTAREA_CLASSES}"
            aria-label="Describe the field situation"
          >${escapeHtml(state.form.analysisPrompt)}</textarea>
        </div>

        <div class="flex flex-col gap-4">
          <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
            <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Run status</p>
            <p class="mt-3 text-base font-semibold tracking-[-0.02em] text-[var(--text)]">${escapeHtml(state.analysis.status)}</p>
            <p id="form-error" style="${state.analysis.error ? "" : "display: none;"}" class="mt-2 text-sm text-[var(--accent-warm)]">${escapeHtml(state.analysis.error)}</p>
            <div class="mt-4 rounded-[22px] border border-[var(--border)] bg-[var(--panel)] px-4 py-3 text-sm text-[var(--text-muted)]">
              <p class="font-semibold text-[var(--text)]">${modeLabel()}</p>
              <p class="mt-1 leading-6">Prototype note: synthetic training data, approximate ET, heuristic confidence, and rule-based optimization remain visible for review.</p>
            </div>
            <div class="mt-5">
              ${PrimaryButton({
                id: "run-analysis-button",
                label: state.analysis.submitting ? "Running..." : "Run analysis",
                iconName: "sparkles",
                variant: "primary",
                type: "submit",
                extraClass: "min-h-[56px] w-full rounded-[22px] text-base",
                disabled: state.analysis.submitting,
              })}
            </div>
            <p class="mt-3 text-xs leading-5 text-[var(--text-muted)]">The recommendation card below is designed to be the first thing a farmer sees after submission.</p>
          </div>

          <details class="tech-details rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
            <summary class="focus-outline flex cursor-pointer items-center justify-between gap-4 rounded-[18px]">
              <div>
                <p class="text-sm font-semibold text-[var(--text)]">Advanced options</p>
                <p class="mt-1 text-sm text-[var(--text-muted)]">Model choice and workspace behaviors stay available without competing with the main call to action.</p>
              </div>
              <span class="tech-chevron transition-transform duration-200">${toggleChevron()}</span>
            </summary>
            <div class="mt-4 space-y-4">
              <label class="block text-sm text-[var(--text-muted)]">
                <span class="mb-2 block text-sm font-semibold text-[var(--text)]">Model</span>
                <select
                  name="model"
                  class="focus-outline min-h-[48px] w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel)] px-3.5 py-3 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
                >
                  ${["Helios Core", "Helios Balanced", "Helios Conservative"]
                    .map((option) => `<option value="${option}" ${state.form.model === option ? "selected" : ""}>${option}</option>`)
                    .join("")}
                </select>
              </label>
              <div class="flex flex-wrap gap-3">
                ${toggleControl("autoSave", "Auto-save run", state.form.autoSave)}
                ${toggleControl("includeNotes", "Detailed notes", state.form.includeNotes)}
              </div>
            </div>
          </details>
        </div>
      </div>
    </section>
  `;
}

function toggleChevron() {
  return `
    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <path d="m6 9 6 6 6-6" />
    </svg>
  `;
}
