import { PAGE_TITLES } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow } from "../domain.js";
import { state, runtimeConfig } from "../state.js";
import {
  PrimaryButton,
  decisionPill,
  emptyBlock,
  emptyInspectorState,
  escapeHtml,
  icon,
} from "./shared.js";

function runMetaLine(run) {
  const parts = [`${formatPercent(run.confidenceScore)} CONF`];
  if (run.decision === "water") {
    parts.push(`${(run.recommendedAmountIn ?? 0).toFixed(2)} IN`);
  } else {
    parts.push("HOLD");
  }
  parts.push(formatWindow(run.timingWindow).toUpperCase());
  return parts.join(" · ");
}

export function ResultCard(run) {
  const isValidation = run.backendSnapshot?.validationMode === true;
  const fieldName = escapeHtml(run.inputSnapshot?.fieldName || "UNTITLED FIELD").toUpperCase();
  const toneClass = run.decision === "water" ? "rail-warm" : "rail-forest";
  const etTag = run.etSource === "openet-live" || run.etSource === "openet-cache"
    ? `<span class="num text-[9px] font-extrabold tracking-[0.14em] rounded px-1.5 py-0.5 bg-[rgba(56,189,248,0.12)] text-[#0284c7]">OpenET LIVE</span>`
    : run.etSource === "openet-fallback"
      ? `<span class="num text-[9px] font-extrabold tracking-[0.14em] rounded px-1.5 py-0.5 bg-[var(--panel-muted)] text-[var(--text-muted)] border border-[var(--border)]">OpenET FALLBACK</span>`
      : "";

  return `
    <article class="metric-card fade-in rounded-[10px] border border-[var(--metric-border)] ${toneClass} transition-all duration-200 hover:border-[var(--border-strong)]">
      <div class="flex flex-wrap items-center gap-3 px-4 py-3">
        ${decisionPill(run.decision)}
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="num text-sm font-extrabold tracking-[0.02em] text-[var(--ink)]">${fieldName}</span>
            <span class="num text-[10px] font-bold tracking-[0.1em] text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</span>
            ${isValidation ? `<span class="num text-[9px] font-extrabold tracking-[0.18em] px-1.5 py-0.5 rounded bg-[var(--accent-warm-soft)] text-[var(--accent-warm)]">VALIDATION</span>` : ""}
            ${etTag}
          </div>
          <p class="num mt-1 text-[11px] font-bold tracking-[0.06em] text-[var(--text-muted)]">${runMetaLine(run)}</p>
        </div>
        <button
          type="button"
          data-copy="${run.id}"
          class="focus-outline inline-flex items-center gap-1.5 rounded-[6px] border border-[var(--border)] bg-[var(--panel-muted)] px-2.5 py-1.5 text-[10px] font-extrabold tracking-[0.14em] text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--border-strong)] hover:text-[var(--ink)]"
        >
          ${icon("copy", "h-3.5 w-3.5")}
          <span>COPY</span>
        </button>
      </div>
      <details class="tech-details border-t border-dashed border-[var(--hairline)]">
        <summary class="focus-outline flex cursor-pointer items-center justify-between gap-3 px-4 py-2.5">
          <span class="num text-[10px] font-extrabold tracking-[0.16em] text-[var(--text-muted)]">TECHNICAL DETAILS</span>
          <span class="tech-chevron text-[var(--text-muted)] transition-transform duration-200">
            ${icon("chevronDown", "h-4 w-4")}
          </span>
        </summary>
        <pre class="overflow-x-auto border-t border-dashed border-[var(--hairline)] bg-[var(--panel-muted)] p-4 font-mono text-[11px] leading-5 text-[var(--text-muted)]">${escapeHtml(run.copyText)}</pre>
      </details>
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
