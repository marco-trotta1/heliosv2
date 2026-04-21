import { state, runtimeConfig, isLiveApiMode } from "../state.js";
import { renderApp } from "../ui.js";
import { apiUrl, readJsonResponse } from "./http.js";
import { buildPredictionRequest, mapApiRun, buildLocalRun } from "./run-builders.js";

export async function evaluateScenario() {
  const inputs = { ...state.form };
  const validationMode = state.backend.validationMode === true;
  if (state.analysis.submitting) {
    return;
  }
  state.analysis.submitting = true;
  state.analysis.error = "";
  state.analysis.status = isLiveApiMode()
    ? validationMode
      ? "Running validation recommendation. Nearby feedback adjustments are disabled."
      : "Running recommendation with nearby feedback..."
    : "Running local demo estimate. No live backend call will be made.";
  renderApp();

  if (!isLiveApiMode()) {
    const run = buildLocalRun(inputs);
    state.acknowledgement.pendingRun = run;
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
    if (!response.ok) {
      const rawText = await response.text();
      let detail = "";
      try {
        const parsed = JSON.parse(rawText);
        detail = typeof parsed?.detail === "string" && parsed.detail.length > 0
          ? parsed.detail
          : rawText.slice(0, 300);
      } catch {
        detail = rawText.slice(0, 300);
      }
      state.analysis.source = "error";
      state.analysis.status = "";
      state.analysis.error = `Recommendation service did not return a valid result. HTTP ${response.status}: ${detail}`;
      return;
    }
    const result = await readJsonResponse(response);
    const run = mapApiRun(inputs, result);
    state.acknowledgement.pendingRun = run;
    state.analysis.source = "api";
    state.analysis.status = validationMode
      ? "Validation recommendation completed. Nearby feedback adjustments remained disabled for clean scoring."
      : run.regionalInsights?.totalSamples
        ? `Recommendation updated using ${run.regionalInsights.totalSamples} nearby feedback reports.`
        : "Recommendation completed. No nearby feedback reports were available yet.";
  } catch (error) {
    state.analysis.source = "error";
    state.analysis.status = "";
    const reason = error instanceof Error ? error.message : "Network or client error.";
    state.analysis.error = `Recommendation service did not return a valid result. ${reason}`;
  } finally {
    state.analysis.submitting = false;
    renderApp();
  }
}
