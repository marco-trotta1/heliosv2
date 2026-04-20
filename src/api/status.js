import { state, isLiveApiMode } from "../state.js";
import { renderApp } from "../ui.js";
import { apiUrl } from "./http.js";

export async function refreshBackendStatus() {
  if (!isLiveApiMode()) {
    return;
  }
  state.backend.status = "checking";
  renderApp();

  let healthy = false;
  try {
    const healthRes = await fetch(apiUrl("/health"));
    healthy = healthRes.ok;
  } catch {
    healthy = false;
  }

  if (!healthy) {
    state.backend.status = "unavailable";
    renderApp();
    return;
  }

  state.backend.status = "ready";
  try {
    const verRes = await fetch(apiUrl("/version"));
    if (verRes.ok) {
      const ver = await verRes.json();
      state.backend.modelHash = typeof ver.model_artifact_hash === "string" ? ver.model_artifact_hash : null;
      state.backend.trainingDate = typeof ver.training_date === "string" ? ver.training_date : null;
      state.backend.apiVersion = typeof ver.api_version === "string" ? ver.api_version : null;
    }
  } catch {
    // version fetch is non-blocking; the ready pill still shows without hash/date
  }
  renderApp();
}
