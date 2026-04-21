import { refreshBackendStatus } from "./src/api.js";
import { applyTheme, state } from "./src/state.js";
import { renderApp } from "./src/ui.js";

if (typeof window !== "undefined") {
  window.__heliosState = state;
  window.__heliosRender = renderApp;
}

applyTheme();
renderApp();
refreshBackendStatus();
