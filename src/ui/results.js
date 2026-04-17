import { PAGE_TITLES } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow, recommendationTone } from "../domain.js";
import { state, runtimeConfig } from "../state.js";
import { PrimaryButton, emptyBlock, emptyInspectorState, escapeHtml, icon } from "./shared.js";

export function ResultCard(run, inspectorMode = false) {
  const tone = recommendationTone(run);
  return `
    <article class="fade-in rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-4 shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--accent)]">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h3 class="truncate text-sm font-medium text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "Untitled field")}</h3>
          <p class="mt-1 text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
        </div>
        <button
          type="button"
          data-copy="${run.id}"
          class="inline-flex items-center gap-1 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs font-medium text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
        >
          ${icon("copy", "h-4 w-4")}
          <span>Copy</span>
        </button>
      </div>
      <div class="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]">
        <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] p-4">
          <p class="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation amount</p>
          <div class="mt-2 flex items-end gap-2">
            <span class="text-3xl font-semibold tracking-tight ${tone.amount}">${(run.recommendedAmountIn ?? 0).toFixed(2)}</span>
            <span class="pb-1 text-sm font-medium text-[var(--text-muted)]">in</span>
          </div>
        </div>
        <div class="flex flex-wrap content-start gap-2">
          <span class="rounded-full px-3 py-1 text-xs font-medium ${tone.pill}">${run.decision.toUpperCase()}</span>
          <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">${formatWindow(run.timingWindow)}</span>
        </div>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">Heuristic confidence ${formatPercent(run.confidenceScore)}</span>
        <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">Stress ${formatPercent(run.stressProbability)}</span>
      </div>
      ${inspectorMode ? `<div class="mt-4 h-px bg-[var(--border)]"></div>` : ""}
      <pre class="mt-4 overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] p-4 font-mono text-[12px] leading-6 text-[var(--text-muted)]">${escapeHtml(run.copyText)}</pre>
    </article>
  `;
}

export function ResultsPanel() {
  return `
    <aside class="col-span-2 border-t border-[var(--border)] bg-[var(--bg)] xl:col-span-1 xl:border-l xl:border-t-0">
      <div class="sticky top-0 flex h-full max-h-screen flex-col">
        <div class="flex h-16 items-center justify-between border-b border-[var(--border)] px-4">
          <div>
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Results</p>
            <h2 class="mt-1 text-base font-medium text-[var(--text)]">Analysis console</h2>
          </div>
          <div class="flex items-center gap-2">
            ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
            <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-xs text-[var(--text-muted)]">
              ${state.runHistory.length} total
            </div>
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <div class="space-y-3">
            ${state.runHistory.length > 0
              ? state.runHistory.slice(0, 8).map((run) => ResultCard(run, true)).join("")
              : emptyInspectorState()}
          </div>
        </div>
      </div>
    </aside>
  `;
}

export function HistoryPage(items, subtitle) {
  return `
    <section class="space-y-6">
      <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${PAGE_TITLES[state.activePage]}</p>
        <h2 class="mt-3 text-2xl font-semibold tracking-tight text-[var(--text)]">${subtitle}</h2>
      </div>
      <div class="space-y-3">
        ${items.length > 0 ? items.map((run) => ResultCard(run)).join("") : emptyBlock("No records yet", "Run an analysis to populate this page.")}
      </div>
    </section>
  `;
}

export function SettingsPage() {
  return `
    <section class="space-y-6">
      <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Settings</p>
        <h2 class="mt-3 text-2xl font-semibold tracking-tight text-[var(--text)]">Workspace preferences</h2>
      </div>
      <div class="grid gap-6 xl:grid-cols-2">
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Theme</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Current theme</h3>
          <p class="mt-3 text-sm text-[var(--text-muted)]">
            Switch between the default dark operating mode and a light workspace for review sessions.
          </p>
          <div class="mt-5">
            ${PrimaryButton({ id: "theme-toggle-inline", label: state.theme === "dark" ? "Switch to light" : "Switch to dark", iconName: state.theme === "dark" ? "sun" : "moon", variant: "secondary" })}
          </div>
        </div>
        <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Deployment</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">Runtime mode</h3>
          <ul class="mt-4 space-y-3 text-sm text-[var(--text-muted)]">
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">Configured mode: ${escapeHtml(runtimeConfig.mode)}</li>
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">API base URL: ${escapeHtml(runtimeConfig.apiBaseUrl || "same-origin or none")}</li>
            <li class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">${escapeHtml(runtimeConfig.disclaimer)}</li>
          </ul>
        </div>
      </div>
    </section>
  `;
}
