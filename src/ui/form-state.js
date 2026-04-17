import { INFILTRATION_RATE_BY_TEXTURE } from "../constants.js";
import { fetchNOAAWeather } from "../api/http.js";
import { state, updateFormField, updateArrayField } from "../state.js";

const AUTO_WEATHER_FIELDS = [
  "temperatureF",
  "humidityPct",
  "windMph",
  "precipitationIn",
  "solarRadiationMjM2",
];

let weatherAutofillTimer = null;

export function parseNumberInput(value, fallback) {
  if (value === "") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function parseFieldValue(target, fallback) {
  if (target.type === "number") {
    return parseNumberInput(target.value, fallback);
  }
  return target.value;
}

export function syncFormState(form) {
  const formData = new FormData(form);
  for (const [key, value] of formData.entries()) {
    if (key === "waterWindow" || key === "energyWindow") {
      continue;
    }
    const field = form.elements.namedItem(key);
    if (field instanceof HTMLInputElement && field.type === "checkbox") {
      state.form[key] = field.checked;
    } else if (field instanceof HTMLInputElement && field.type === "number") {
      state.form[key] = parseNumberInput(value, state.form[key]);
    } else {
      state.form[key] = value;
    }
  }
  state.form.waterWindow = [...form.querySelectorAll('input[name="waterWindow"]:checked')].map((item) => item.value);
  state.form.energyWindow = [...form.querySelectorAll('input[name="energyWindow"]:checked')].map((item) => item.value);
}

export function autoSizeTextarea(textarea) {
  textarea.style.height = "0px";
  textarea.style.height = `${textarea.scrollHeight}px`;
}

export function resizePromptInput() {
  const prompt = document.querySelector("#analysis-prompt");
  if (prompt) {
    autoSizeTextarea(prompt);
  }
}

function validCoordinates(lat, lon) {
  return Number.isFinite(lat) && lat >= -90 && lat <= 90 && Number.isFinite(lon) && lon >= -180 && lon <= 180;
}

async function runWeatherAutofill(renderApp) {
  const form = document.querySelector("#analysis-form");
  const lat = Number(state.form.locationLat);
  const lon = Number(state.form.locationLon);
  if (!form || state.activePage !== "run-analysis" || !validCoordinates(lat, lon)) {
    return;
  }

  const requestKey = `${lat.toFixed(4)},${lon.toFixed(4)}`;
  if (state.weatherAutofill.loading && state.weatherAutofill.requestKey === requestKey) {
    return;
  }
  if (state.weatherAutofill.appliedKey === requestKey) {
    return;
  }

  state.weatherAutofill.loading = true;
  state.weatherAutofill.requestKey = requestKey;
  state.weatherAutofill.autoFields = {};

  const weather = await fetchNOAAWeather(lat, lon);
  if (!weather || state.weatherAutofill.requestKey !== requestKey) {
    state.weatherAutofill.loading = false;
    return;
  }

  AUTO_WEATHER_FIELDS.forEach((fieldName) => {
    updateFormField(fieldName, weather[fieldName]);
    const input = form.elements.namedItem(fieldName);
    if (input instanceof HTMLInputElement) {
      input.value = String(weather[fieldName]);
    }
  });

  state.weatherAutofill.loading = false;
  state.weatherAutofill.appliedKey = requestKey;
  state.weatherAutofill.autoFields = Object.fromEntries(AUTO_WEATHER_FIELDS.map((fieldName) => [fieldName, true]));
  renderApp();
}

export function scheduleWeatherAutofill(renderApp, delayMs = 0) {
  window.clearTimeout(weatherAutofillTimer);
  weatherAutofillTimer = window.setTimeout(() => {
    runWeatherAutofill(renderApp);
  }, delayMs);
}

export function updateFormStateFromInput(target, form, scheduleAutofill) {
  if (target instanceof HTMLInputElement && target.type === "checkbox") {
    if (target.name === "waterWindow" || target.name === "energyWindow") {
      updateArrayField(target.name, target.value, target.checked);
    } else {
      updateFormField(target.name, target.checked);
    }
    return;
  }

  if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement) {
    updateFormField(target.name, parseFieldValue(target, state.form[target.name]));
    if (target.name === "soilTexture") {
      const defaultRate = INFILTRATION_RATE_BY_TEXTURE[target.value];
      if (defaultRate != null) {
        updateFormField("infiltrationRate", defaultRate);
        const infiltrationInput = form.elements.namedItem("infiltrationRate");
        if (infiltrationInput instanceof HTMLInputElement) {
          infiltrationInput.value = defaultRate;
        }
      }
    }
    if (target.name === "locationLat" || target.name === "locationLon") {
      state.weatherAutofill.appliedKey = "";
      state.weatherAutofill.autoFields = {};
      scheduleAutofill(400);
    }
  }
}
