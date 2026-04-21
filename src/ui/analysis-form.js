import { PRESETS } from "../constants.js";
import { isLiveApiMode, state } from "../state.js";
import {
  PrimaryButton,
  autoWeatherTag,
  checkboxGroup,
  escapeHtml,
  inputGroup,
  numericInput,
  selectInput,
  stackedCard,
  textInput,
  toggleControl,
} from "./shared.js";

const PROMPT_TEXTAREA_CLASSES = [
  "focus-outline",
  "mt-8",
  "sm:mt-10",
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

function fieldProfileSummary() {
  const parts = [];
  if (state.form.soilTexture) parts.push(String(state.form.soilTexture).toUpperCase());
  if (state.form.cropType) {
    const crop = String(state.form.cropType);
    const stage = state.form.growthStage ? ` · ${String(state.form.growthStage).replace(/_/g, " ")}` : "";
    parts.push(`${crop.toUpperCase()}${stage.toUpperCase()}`);
  }
  if (state.form.fieldAreaAcres) parts.push(`${state.form.fieldAreaAcres}AC`);
  return parts.join(" · ") || "FIELD, CROP, SOIL, LOCATION";
}

function conditionsSummary() {
  const parts = [];
  if (state.form.currentMoisture != null && state.form.currentMoisture !== "") {
    parts.push(`${(Number(state.form.currentMoisture) * 100).toFixed(0)}% VWC`);
  }
  if (state.form.temperatureF != null && state.form.temperatureF !== "") {
    parts.push(`${Math.round(Number(state.form.temperatureF))}°F`);
  }
  if (state.form.windMph != null && state.form.windMph !== "") {
    parts.push(`${Math.round(Number(state.form.windMph))} MPH`);
  }
  if (state.form.precipitationIn != null && state.form.precipitationIn !== "") {
    parts.push(`${Number(state.form.precipitationIn).toFixed(2)}IN RAIN`);
  }
  return parts.join(" · ") || "MOISTURE, TEMP, WIND, FORECAST";
}

function irrigationSummary() {
  const parts = [];
  if (state.form.irrigationType) parts.push(String(state.form.irrigationType).toUpperCase());
  if (state.form.maxIrrigationVolume) parts.push(`MAX ${Number(state.form.maxIrrigationVolume).toFixed(2)}IN`);
  if (Array.isArray(state.form.waterWindow) && state.form.waterWindow.length > 0) {
    parts.push(`${state.form.waterWindow.length} WINDOW${state.form.waterWindow.length > 1 ? "S" : ""}`);
  }
  return parts.join(" · ") || "SYSTEM, CAPS, WINDOWS";
}

function FieldProfileSection() {
  return stackedCard({
    label: "FIELD",
    iconChar: "🌱",
    summary: fieldProfileSummary(),
    content: `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Field name", textInput("fieldName", state.form.fieldName))}
      ${inputGroup("Farm ID", textInput("farmId", state.form.farmId))}
      ${inputGroup("Field area (ac)", numericInput("fieldAreaAcres", state.form.fieldAreaAcres, "1"))}
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
      ${inputGroup("Infiltration rate (in/hr)", numericInput("infiltrationRate", state.form.infiltrationRate, "0.01"))}
      ${inputGroup("Slope (%)", numericInput("slopePct", state.form.slopePct, "0"))}
      ${inputGroup("Latitude", numericInput("locationLat", state.form.locationLat, "-90", "0.0001", "90"))}
      ${inputGroup("Longitude", numericInput("locationLon", state.form.locationLon, "-180", "0.0001", "180"))}
    </div>`,
  });
}

function SensorFeedSection() {
  return stackedCard({
    label: "CONDITIONS",
    iconChar: "🌤",
    summary: conditionsSummary(),
    content: `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Current soil moisture (0–1 VWC)", numericInput("currentMoisture", state.form.currentMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("Moisture 6h ago (0–1 VWC)", numericInput("lagOneMoisture", state.form.lagOneMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("Moisture 12h ago (0–1 VWC)", numericInput("lagTwoMoisture", state.form.lagTwoMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("Temperature (°F)", numericInput("temperatureF", state.form.temperatureF, "-58"), autoWeatherTag("temperatureF"))}
      ${inputGroup("Humidity (%)", numericInput("humidityPct", state.form.humidityPct, "0", "1", "100"), autoWeatherTag("humidityPct"))}
      ${inputGroup("Wind (mph)", numericInput("windMph", state.form.windMph, "0"), autoWeatherTag("windMph"))}
      ${inputGroup("Forecast precipitation (in)", numericInput("precipitationIn", state.form.precipitationIn, "0"), autoWeatherTag("precipitationIn"))}
      ${inputGroup("Solar radiation (MJ/m²)", numericInput("solarRadiationMjM2", state.form.solarRadiationMjM2, "0"), autoWeatherTag("solarRadiationMjM2"))}
      ${inputGroup("Soil moisture sensors", numericInput("sensorCount", state.form.sensorCount, "0", "1", "10"))}
    </div>`,
  });
}

function OperationsSection() {
  return stackedCard({
    label: "IRRIGATION",
    iconChar: "💧",
    summary: irrigationSummary(),
    content: `<div class="grid gap-5 md:grid-cols-2">
      ${inputGroup("Irrigation type", selectInput("irrigationType", state.form.irrigationType, [
        { value: "pivot", label: "Pivot" },
        { value: "drip", label: "Drip" },
        { value: "flood", label: "Flood" },
      ]))}
      ${inputGroup("Pump capacity (in/hr)", numericInput("pumpCapacity", state.form.pumpCapacity, "0.01"))}
      ${inputGroup("Max irrigation volume (in)", numericInput("maxIrrigationVolume", state.form.maxIrrigationVolume, "0"))}
      ${inputGroup("Budget ($)", numericInput("budgetDollars", state.form.budgetDollars, "0", "1"))}
      ${inputGroup("Irrigation last 24h (in)", numericInput("recentIrrigation24h", state.form.recentIrrigation24h, "0"))}
      ${inputGroup("Irrigation last 72h (in)", numericInput("recentIrrigation72h", state.form.recentIrrigation72h, "0"))}
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
  });
}

export function DataSection() {
  return `
    <section>
      <div class="flex items-center justify-between pb-3">
        <p class="eyebrow">FIELD INPUTS</p>
        <span class="num text-[10px] font-bold tracking-[0.12em] text-[var(--text-muted)]">TAP TO EDIT</span>
      </div>
      <div class="grid gap-3">
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
  const apiVersion = state.backend.apiVersion ? ` • API ${state.backend.apiVersion}` : "";
  if (state.backend.validationMode === true) {
    return `Validation build ${hash} • trained ${trained}${apiVersion}`;
  }
  return `Live model ${hash} • trained ${trained}${apiVersion}`;
}

function validationStatusMessage() {
  if (!isLiveApiMode() || state.backend.validationMode !== true) {
    return "";
  }
  return "Validation mode is enabled. Nearby feedback adjustments are disabled so tomorrow's field scoring stays clean.";
}

export function PromptInput() {
  return `
    <section class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-7 shadow-[var(--shadow-strong)] sm:p-8">
      <div class="grid gap-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(290px,0.75fr)]">
        <div>
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--accent)]">Decision Brief</p>
          <h2 class="mt-2 text-[32px] font-semibold tracking-[-0.04em] text-[var(--text)]">Describe the field and the decision</h2>
          <div class="mt-6 flex flex-wrap gap-3">
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
                    class="focus-outline inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-2.5 text-sm font-semibold text-[var(--text)] transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--panel)]"
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

        <div class="flex flex-col gap-5">
          <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] p-6">
            <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Run status</p>
            <p class="mt-3 text-base font-semibold tracking-[-0.02em] text-[var(--text)]">${escapeHtml(state.analysis.status)}</p>
            <p id="form-error" style="${state.analysis.error ? "" : "display: none;"}" class="mt-2 text-sm text-[var(--accent-warm)]">${escapeHtml(state.analysis.error)}</p>
            <div class="mt-5 rounded-[22px] border border-[var(--border)] bg-[var(--panel)] px-4 py-3 text-sm font-semibold text-[var(--text)]">
              ${modeLabel()}
            </div>
            ${validationStatusMessage()
              ? `<div class="validation-banner mt-3"><div><p class="eyebrow" style="color: var(--accent-warm);">VALIDATION MODE</p><p class="mt-1 text-[13px] leading-5 text-[var(--text)]">${validationStatusMessage()}</p></div></div>`
              : ""}
            <div class="mt-6">
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
          </div>

          <details class="tech-details rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] p-6">
            <summary class="focus-outline flex cursor-pointer items-center justify-between gap-4 rounded-[18px]">
              <div>
                <p class="text-sm font-semibold text-[var(--text)]">Advanced options</p>
              </div>
              <span class="tech-chevron transition-transform duration-200">${toggleChevron()}</span>
            </summary>
            <div class="mt-5 space-y-4">
              <label class="block text-sm text-[var(--text-muted)]">
                <span class="mb-2 block text-sm font-semibold text-[var(--text)]">Model</span>
                <select
                  name="model"
                  class="focus-outline min-h-[48px] w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel)] px-4 py-3.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
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
