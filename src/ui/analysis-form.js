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
  "mt-5",
  "w-full",
  "rounded-[24px]",
  "border",
  "border-[var(--border)]",
  "bg-[var(--panel-muted)]",
  "px-4",
  "py-4",
  "text-sm",
  "leading-7",
  "text-[var(--text)]",
  "outline-none",
  "transition-all",
  "duration-200",
  "focus:border-[var(--accent)]",
].join(" ");

function FieldProfileSection() {
  return fieldCard(
    "Field Profile",
    "Crop, soil, and terrain descriptors",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Field name", textInput("fieldName", state.form.fieldName))}
      ${inputGroup("Farm ID", textInput("farmId", state.form.farmId))}
      ${inputGroup("Field area (ac)", numericInput("fieldAreaAcres", state.form.fieldAreaAcres, "1"))}
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
      ${inputGroup("Infiltration rate (in/hr)", numericInput("infiltrationRate", state.form.infiltrationRate, "0.01"))}
      ${inputGroup("Slope (%)", numericInput("slopePct", state.form.slopePct, "0"))}
    </div>`,
  );
}

function SensorFeedSection() {
  return fieldCard(
    "Sensor Feed",
    "Soil moisture and weather inputs",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
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
  );
}

export function DataSection() {
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

export function PromptInput() {
  let modeLabel;
  if (!isLiveApiMode()) {
    modeLabel = "Demo mode";
  } else if (state.backend.status === "checking") {
    modeLabel = "Warming up backend…";
  } else if (state.backend.status === "unavailable") {
    modeLabel = "Backend unavailable";
  } else {
    const hash = state.backend.modelHash ? state.backend.modelHash.slice(0, 7) : "unknown";
    const trained = state.backend.trainingDate ? state.backend.trainingDate.slice(0, 10) : "unknown date";
    modeLabel = `Live • model ${hash} • trained ${trained}`;
  }
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
            .map((key) => PrimaryButton({ label: key === "heatwave" ? "Heat wave" : key === "balanced" ? "Balanced day" : key === "kimberly" ? "Kimberly Farm" : "Rain incoming", iconName: "sparkles", variant: "secondary", extraClass: "preset-trigger", id: "", type: "button" }).replace("<button", `<button data-preset="${key}"`))
            .join("")}
        </div>
      </div>
      <textarea
        id="analysis-prompt"
        name="analysisPrompt"
        rows="4"
        class="${PROMPT_TEXTAREA_CLASSES}"
        aria-label="Describe the field situation"
      >${escapeHtml(state.form.analysisPrompt)}</textarea>
      <div class="mt-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div class="flex flex-1 flex-col gap-4">
          <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-sm text-[var(--text-muted)]">
            <p>${escapeHtml(state.analysis.status)}</p>
            <p id="form-error" style="${state.analysis.error ? "" : "display: none;"}" class="mt-2 text-[var(--accent-warm)]">${escapeHtml(state.analysis.error)}</p>
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
