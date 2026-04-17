import { state, isLiveApiMode, persistState } from "../state.js";
import { renderApp } from "../ui.js";
import { apiUrl, readJsonResponse } from "./http.js";
import { refreshRegionalInsights } from "./run-builders.js";

const HELIOS_ACKNOWLEDGEMENTS_KEY = "helios_acknowledgements";
const FEEDBACK_QUEUE_KEY = "helios-feedback-queue";

export async function logAcknowledgement(run) {
  const fieldId = run.inputSnapshot?.farmId || run.inputSnapshot?.fieldName || "";
  const farmId = run.inputSnapshot?.farmId || "";
  const timestamp = new Date().toISOString();
  const recommendationSummary = run.summary || "";

  if (!isLiveApiMode()) {
    try {
      const stored = JSON.parse(localStorage.getItem(HELIOS_ACKNOWLEDGEMENTS_KEY) || "[]");
      stored.push({ field_id: fieldId, timestamp, recommendation_summary: recommendationSummary });
      localStorage.setItem(HELIOS_ACKNOWLEDGEMENTS_KEY, JSON.stringify(stored));
    } catch {
      // Non-blocking
    }
    return;
  }

  try {
    await fetch(apiUrl("/api/acknowledgements"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        field_id: fieldId,
        farm_id: farmId,
        timestamp,
        recommendation_summary: recommendationSummary,
      }),
    });
  } catch {
    console.error("[helios] Failed to log acknowledgement — proceeding anyway");
  }
}

export async function submitFeedback() {
  if (!state.latestRun || state.feedbackForm.submitting) {
    return;
  }

  const payload = {
    farm_id: state.latestRun.inputSnapshot.farmId,
    timestamp: new Date().toISOString(),
    crop_type: state.latestRun.inputSnapshot.cropType,
    soil_texture: state.latestRun.inputSnapshot.soilTexture,
    irrigation_type: state.latestRun.inputSnapshot.irrigationType,
    growth_stage: state.latestRun.inputSnapshot.growthStage,
    recommendation_type: "irrigation",
    recommendation_value: String(state.latestRun.recommendedAmountIn),
    outcome: state.feedbackForm.outcome,
    yield_delta: state.feedbackForm.yieldDelta === "" ? null : Number(state.feedbackForm.yieldDelta),
    notes: state.feedbackForm.notes.trim() || null,
    location_lat: Number(state.latestRun.inputSnapshot.locationLat),
    location_lon: Number(state.latestRun.inputSnapshot.locationLon),
  };

  if (!isLiveApiMode()) {
    const queue = JSON.parse(localStorage.getItem(FEEDBACK_QUEUE_KEY) || "[]");
    queue.push({ ...payload, queued_at: new Date().toISOString() });
    localStorage.setItem(FEEDBACK_QUEUE_KEY, JSON.stringify(queue));
    state.feedbackForm.status = "Feedback stored locally and will be sent when the backend is available.";
    state.feedbackForm.error = "";
    state.feedbackForm.open = false;
    renderApp();
    return;
  }

  state.feedbackForm.submitting = true;
  state.feedbackForm.error = "";
  state.feedbackForm.status = "";
  renderApp();

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
