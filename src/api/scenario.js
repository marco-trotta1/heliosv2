import { state, runtimeConfig, isLiveApiMode } from "../state.js";
import { renderApp } from "../ui.js";
import { apiUrl, readJsonResponse } from "./http.js";
import { buildPredictionRequest, mapApiRun, buildLocalRun } from "./run-builders.js";

export async function evaluateScenario() {
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
    const result = await readJsonResponse(response);
    if (!response.ok) {
      throw new Error(result.detail || "Unable to run the recommendation service.");
    }
    const run = mapApiRun(inputs, result);
    state.acknowledgement.pendingRun = run;
    state.analysis.source = "api";
    state.analysis.status = run.regionalInsights?.totalSamples
      ? `Recommendation updated using ${run.regionalInsights.totalSamples} nearby feedback reports.`
      : "Recommendation completed. No nearby feedback reports were available yet.";
  } catch (error) {
    const run = buildLocalRun(inputs);
    state.acknowledgement.pendingRun = run;
    state.analysis.source = "local";
    state.analysis.error = error instanceof Error ? error.message : "Unable to reach the recommendation service.";
    state.analysis.status = "Showing the local demo estimate because the live API could not be reached.";
  } finally {
    state.analysis.submitting = false;
    renderApp();
  }
}
