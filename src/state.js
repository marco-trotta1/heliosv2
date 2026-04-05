import {
  DEFAULT_FORM,
  DEFAULT_RUNTIME_CONFIG,
  PRESETS,
  RUN_HISTORY_KEY,
  SAVED_RUNS_KEY,
  THEME_KEY,
} from "./constants.js";
import { serializeRunForCopy } from "./domain.js";
// NOTE: This creates a circular dependency with ui.js. It works because renderApp
// is only called inside function bodies (never at top-level evaluation time).
// Do NOT call renderApp at the module top level.
import { renderApp } from "./ui.js";

// ── Runtime config ─────────────────────────────────────────────────────────────

export function normalizeRuntimeConfig(config) {
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

export const runtimeConfig = normalizeRuntimeConfig(window.HELIOS_CONFIG || DEFAULT_RUNTIME_CONFIG);

export function isLiveApiMode() {
  return runtimeConfig.mode === "live";
}

// ── Stored arrays ──────────────────────────────────────────────────────────────

export function loadStoredArray(key) {
  try {
    const value = window.localStorage.getItem(key);
    return value ? JSON.parse(value).map(normalizeRun).filter(Boolean) : [];
  } catch {
    return [];
  }
}

export function normalizeRun(run) {
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
  const hadMissingId = !run.id;
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
  if (hadMissingId) {
    console.warn("[helios] normalizeRun: run was missing id, generated fallback:", normalized.id);
  }
  return normalized;
}

// ── Application state ──────────────────────────────────────────────────────────

export const state = {
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
  weatherAutofill: {
    requestKey: "",
    appliedKey: "",
    loading: false,
    autoFields: {},
  },
  analysisConsoleOpen: false,
  acknowledgement: {
    pendingRun: null,
  },
};

if (state.runHistory.length > 0) {
  state.latestRun = state.runHistory[0];
}

// ── Persistence ────────────────────────────────────────────────────────────────

export function persistState() {
  window.localStorage.setItem(RUN_HISTORY_KEY, JSON.stringify(state.runHistory));
  window.localStorage.setItem(SAVED_RUNS_KEY, JSON.stringify(state.savedRuns));
  window.localStorage.setItem(THEME_KEY, state.theme);
}

// ── Run management ─────────────────────────────────────────────────────────────

export function dedupeRuns(runs) {
  const seen = new Set();
  return runs.filter((run) => {
    if (seen.has(run.id)) {
      return false;
    }
    seen.add(run.id);
    return true;
  });
}

export function storeRun(run) {
  state.latestRun = run;
  state.feedbackForm.open = false;
  state.feedbackForm.status = "";
  state.feedbackForm.error = "";
  state.feedbackForm.yieldDelta = "";
  state.feedbackForm.notes = "";
  state.runHistory.unshift(run);
  state.runHistory = dedupeRuns(state.runHistory).slice(0, 50);
  if (state.form.autoSave) {
    state.savedRuns.unshift(run);
    state.savedRuns = dedupeRuns(state.savedRuns).slice(0, 50);
  }
  persistState();
}

export function saveLatestRun() {
  if (!state.latestRun) {
    return;
  }
  state.savedRuns.unshift(state.latestRun);
  state.savedRuns = dedupeRuns(state.savedRuns).slice(0, 50);
  persistState();
  renderApp();
}

// ── Navigation & theme ─────────────────────────────────────────────────────────

export function setPage(pageId) {
  state.activePage = pageId;
  renderApp();
}

export function applyTheme() {
  document.body.classList.toggle("theme-light", state.theme === "light");
}

export function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  applyTheme();
  persistState();
  renderApp();
}

export function applyPreset(name) {
  if (!PRESETS[name]) {
    return;
  }
  state.form = { ...PRESETS[name] };
  state.activePage = "run-analysis";
  renderApp();
}

// ── Form field helpers ─────────────────────────────────────────────────────────

export function updateFormField(name, value) {
  state.form[name] = value;
}

export function updateArrayField(name, nextValue, checked) {
  const current = new Set(state.form[name]);
  if (checked) {
    current.add(nextValue);
  } else {
    current.delete(nextValue);
  }
  state.form[name] = [...current];
}
