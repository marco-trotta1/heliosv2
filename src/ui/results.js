import { PAGE_TITLES } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow } from "../domain.js";
import { state, runtimeConfig } from "../state.js";
import { PrimaryButton, emptyBlock, emptyInspectorState, escapeHtml, icon } from "./shared.js";

function technicalDetails(run) {
  return `
    <details class="tech-details mt-4 rounded-[22px] border border-[var(--border)] bg-[var(--panel-muted)] p-3">
      <summary class="focus-outline flex cursor-pointer items-center justify-between gap-3 rounded-[16px] px-2 py-1">
        <span class="text-sm font-semibold text-[var(--text)]">Technical details</span>
        <span class="tech-chevron text-[var(--text-muted)] transition-transform duration-200">
          ${icon("chevronDown", "h-4 w-4")}
        </span>
      </summary>
      <pre class="mt-3 overflow-x-auto rounded-[18px] border border-[var(--border)] bg-[var(--panel)] p-4 font-mono text-[12px] leading-6 text-[var(--text-muted)]">${escapeHtml(run.copyText)}</pre>
    </details>
  `;
}

export function ResultCard(run, inspectorMode = false) {
  const decisionPillClass = run.decision === "water" ? "pill-water" : "pill-wait";
  const amountClass = run.decision === "water" ? "tone-water" : "tone-wait";

  return `
    <article class="fade-in rounded-[30px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--border-strong)]">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">${formatTimestamp(run.timestamp)}</p>
          <h3 class="mt-2 truncate text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "Untitled field")}</h3>
        </div>
        <button
          type="button"
          data-copy="${run.id}"
          class="focus-outline inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs font-semibold text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--border-strong)] hover:text-[var(--text)]"
        >
          ${icon("copy", "h-4 w-4")}
          <span>Copy</span>
        </button>
      </div>

      <div class="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div class="rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] ${decisionPillClass}">
              ${run.decision.toUpperCase()}
            </span>
            <span class="rounded-full bg-[var(--panel)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">${formatWindow(run.timingWindow)}</span>
          </div>
          <div class="mt-4 flex items-end gap-2">
            <span class="text-4xl font-semibold tracking-[-0.05em] ${amountClass}">${(run.recommendedAmountIn ?? 0).toFixed(2)}</span>
            <span class="pb-1 text-sm font-semibold text-[var(--text-muted)]">in</span>
          </div>
        </div>
        <div class="flex flex-wrap content-start gap-2 lg:max-w-[180px] lg:justify-end">
          ${run.backendSnapshot?.validationMode
            ? `<span class="rounded-full bg-[var(--accent-warm-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent-warm)]">Validation build</span>`
            : ""}
          <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">Heuristic confidence ${formatPercent(run.confidenceScore)}</span>
          <span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">Stress ${formatPercent(run.stressProbability)}</span>
          ${run.etSource === "openet-live" || run.etSource === "openet-cache"
            ? `<span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">ET live</span>`
            : run.etSource === "openet-fallback"
              ? `<span class="rounded-full bg-[var(--panel-muted)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">ET estimate</span>`
              : ""}
        </div>
      </div>

      ${technicalDetails(run)}
      ${inspectorMode ? `<div class="mt-1 h-px bg-transparent"></div>` : ""}
    </article>
  `;
}

export function ResultsPanel() {
  return `
    <aside class="col-span-2 border-t border-[var(--border)] bg-[var(--bg)] xl:col-span-1 xl:border-l xl:border-t-0">
      <div class="sticky top-0 flex h-full max-h-screen flex-col">
        <div class="flex h-20 items-center justify-between border-b border-[var(--border)] px-4">
          <div>
            <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Recent Runs</p>
            <h2 class="mt-1 text-base font-semibold text-[var(--text)]">Field decisions</h2>
          </div>
          <div class="flex items-center gap-2">
            ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
            <div class="rounded-full border border-[var(--border)] bg-[var(--panel)] px-3 py-1.5 text-xs font-semibold text-[var(--text-muted)]">
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
      <div class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-7 shadow-[var(--shadow-strong)]">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">${PAGE_TITLES[state.activePage]}</p>
        <h2 class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">${subtitle}</h2>
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
      <div class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-7 shadow-[var(--shadow-strong)]">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Settings</p>
        <h2 class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">Workspace preferences</h2>
      </div>
      <div class="grid gap-6 xl:grid-cols-2">
        <div class="rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Theme</p>
          <h3 class="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--text)]">Current theme</h3>
          <div class="mt-5">
            ${PrimaryButton({ id: "theme-toggle-inline", label: state.theme === "dark" ? "Switch to light" : "Switch to dark", iconName: state.theme === "dark" ? "sun" : "moon", variant: "secondary" })}
          </div>
        </div>
        <div class="rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Deployment</p>
          <h3 class="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--text)]">Runtime mode</h3>
          <ul class="mt-4 space-y-3 text-sm text-[var(--text-muted)]">
            <li class="rounded-[22px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">Configured mode: ${escapeHtml(runtimeConfig.mode)}</li>
            <li class="rounded-[22px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">API base URL: ${escapeHtml(runtimeConfig.apiBaseUrl || "same-origin or none")}</li>
            <li class="rounded-[22px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3">${escapeHtml(runtimeConfig.disclaimer)}</li>
          </ul>
        </div>
      </div>
    </section>
  `;
}
