import { state } from "./state.js";
import { PromptInput, DataSection } from "./ui/analysis-form.js";
import { AnalysisConsoleDisclosure, RecommendationSpotlight } from "./ui/analysis-spotlight.js";
import { DashboardPage } from "./ui/dashboard.js";
import { bindAppEvents as bindAppEventsImpl } from "./ui/events.js";
import { scheduleWeatherAutofill } from "./ui/form-state.js";
import { Sidebar, TopBar } from "./ui/layout.js";
import { HistoryPage, ResultsPanel, SettingsPage } from "./ui/results.js";

const app = document.querySelector("#app");

function AnalysisWorkspace() {
  return `
    <section class="space-y-6">
      <form id="analysis-form" novalidate class="space-y-6">
        ${PromptInput()}
        ${RecommendationSpotlight()}
        ${DataSection()}
        ${AnalysisConsoleDisclosure()}
      </form>
    </section>
  `;
}

function renderPage() {
  if (state.activePage === "dashboard") {
    return DashboardPage();
  }
  if (state.activePage === "history") {
    return HistoryPage(state.runHistory, "All analysis runs");
  }
  if (state.activePage === "saved") {
    return HistoryPage(state.savedRuns, "Pinned runs and reusable scenarios");
  }
  if (state.activePage === "settings") {
    return SettingsPage();
  }
  return AnalysisWorkspace();
}

export function bindAppEvents() {
  bindAppEventsImpl({
    renderApp,
    scheduleWeatherAutofill,
  });
}

export function renderApp() {
  const showResultsPanel = state.activePage !== "run-analysis";
  app.innerHTML = `
    <div class="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <div class="grid min-h-screen ${showResultsPanel ? "grid-cols-[78px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_420px]" : "grid-cols-[78px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)]"}">
        ${Sidebar()}
        <div class="min-w-0">
          ${TopBar()}
          <main class="glass-grid min-h-[calc(100vh-65px)] px-4 py-4 sm:px-6 sm:py-6">
            ${renderPage()}
          </main>
        </div>
        ${showResultsPanel ? ResultsPanel() : ""}
      </div>
    </div>
  `;
  window.tailwind?.refresh?.();
  bindAppEvents();
  scheduleWeatherAutofill(renderApp);
}
