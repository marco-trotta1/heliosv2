import { PRESETS } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow, recommendationTone } from "../domain.js";
import { state, runtimeConfig } from "../state.js";
import { emptyBlock, escapeHtml, icon } from "./shared.js";

function dashboardRunItem(run) {
  const tone = recommendationTone(run);
  return `
    <article class="fade-in rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="text-sm font-medium text-[var(--text)]">${escapeHtml(run.inputSnapshot.fieldName)}</p>
          <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="shrink-0 text-right">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
          <div class="mt-3 flex flex-wrap justify-end gap-2">
            <span class="rounded-full px-3 py-1 text-xs font-medium ${tone.pill}">${run.decision.toUpperCase()}</span>
            <span class="rounded-full bg-[var(--panel)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">${(run.recommendedAmountIn ?? 0).toFixed(2)} in</span>
          </div>
        </div>
      </div>
    </article>
  `;
}

function DashboardMetric(label, value, hint, emphasisClass = "") {
  return `
    <div class="flex flex-col gap-2 rounded-3xl bg-[var(--panel-muted)] px-4 py-4">
      <p class="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${label}</p>
      <p class="text-3xl font-semibold tracking-tight ${emphasisClass || "text-[var(--text)]"}">${value}</p>
      <p class="text-sm text-[var(--text-muted)]">${hint}</p>
    </div>
  `;
}

function DashboardMetrics(totalRuns, savedRuns) {
  const latestRun = state.latestRun;
  const metrics = latestRun
    ? [
        {
          label: "Confidence",
          value: formatPercent(latestRun.confidenceScore),
          hint: "Heuristic confidence on the latest recommendation.",
        },
        {
          label: "Stress Risk",
          value: formatPercent(latestRun.stressProbability),
          hint: "Estimated crop stress risk if the field waits.",
        },
        {
          label: "What Matters Next",
          value: escapeHtml(formatWindow(latestRun.timingWindow)),
          hint: "Preferred operating window from the latest run.",
        },
      ]
    : [
        {
          label: "Recent Runs",
          value: `${totalRuns}`,
          hint: "Analyses currently available in local history.",
        },
        {
          label: "Saved Analyses",
          value: `${savedRuns}`,
          hint: "Pinned scenarios ready for quick review.",
        },
        {
          label: "Workspace Mode",
          value: runtimeConfig.mode === "live" ? "Live API" : "Demo mode",
          hint: "Current workspace mode.",
        },
      ];
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-4 shadow-[var(--shadow)]">
      <div class="px-2 pb-4 pt-2">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Key Metrics</p>
      </div>
      <div class="grid gap-3 md:grid-cols-3">
        ${metrics.map((metric) => DashboardMetric(metric.label, metric.value, metric.hint)).join("")}
      </div>
    </section>
  `;
}

function DashboardSection(eyebrow, title, body, content, action = "") {
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="max-w-2xl">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${eyebrow}</p>
          <h3 class="mt-2 text-lg font-medium text-[var(--text)]">${title}</h3>
          <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">${body}</p>
        </div>
        ${action}
      </div>
      <div class="mt-5">${content}</div>
    </section>
  `;
}

function DashboardHeroStatus() {
  if (!state.latestRun) {
    return `
      <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Current Status</p>
        <div class="mt-4 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div class="max-w-3xl">
            <h2 class="text-3xl font-semibold tracking-tight text-[var(--text)]">No recent irrigation recommendation</h2>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
              Start a run to surface the current irrigation call, timing window, and supporting field context in one place.
            </p>
          </div>
          <button
            type="button"
            data-nav="run-analysis"
            class="inline-flex items-center gap-2 rounded-2xl bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:bg-[var(--accent-hover)]"
          >
            ${icon("sparkles", "h-4 w-4")}
            <span>Run analysis</span>
          </button>
        </div>
      </section>
    `;
  }

  const run = state.latestRun;
  const tone = recommendationTone(run);
  return `
    <section class="accent-divider rounded-[28px] border p-6 shadow-[var(--shadow)] ${tone.spotlight}">
      <div class="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div class="max-w-3xl">
          <div class="flex flex-wrap items-center gap-3">
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Current Status</p>
            <span class="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${tone.pill}">
              ${run.decision === "water" ? "Water now" : "Hold"}
            </span>
          </div>
          <h2 class="mt-4 text-3xl font-semibold tracking-tight text-[var(--text)]">${run.decision === "water" ? `Apply ${(run.recommendedAmountIn ?? 0).toFixed(2)} in ${escapeHtml(formatWindow(run.timingWindow)).toLowerCase()}` : "Hold irrigation for now"}</h2>
          <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 xl:min-w-[320px] xl:grid-cols-1">
          <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] px-4 py-4">
            <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Most recent field</p>
            <p class="mt-2 text-lg font-medium text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "Untitled field")}</p>
            <p class="mt-2 text-sm text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
          </div>
          <button
            type="button"
            data-nav="run-analysis"
            class="inline-flex items-center justify-center gap-2 rounded-3xl border border-[var(--border)] bg-[var(--panel)] px-4 py-4 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--accent)]"
          >
            ${icon("sparkles", "h-4 w-4")}
            <span>Open Run Analysis</span>
          </button>
        </div>
      </div>
    </section>
  `;
}

export function DashboardPage() {
  const totalRuns = state.runHistory.length;
  const savedRuns = state.savedRuns.length;
  return `
    <section class="space-y-6">
      ${DashboardHeroStatus()}
      ${DashboardMetrics(totalRuns, savedRuns)}
      <div class="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        ${DashboardSection(
          "Activity",
          "Recent field decisions",
          "The latest analyses stay visible here for quick review without crowding the main status.",
          `<div class="space-y-3">
            ${state.runHistory.slice(0, 3).map((run) => dashboardRunItem(run)).join("") || emptyBlock("No runs yet", "Start with Run Analysis to populate the dashboard feed.")}
          </div>`,
          `<button
            type="button"
            data-nav="run-analysis"
            class="inline-flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--accent)]"
          >
            ${icon("sparkles", "h-4 w-4")}
            <span>New analysis</span>
          </button>`,
        )}
        ${DashboardSection(
          "Quick Start",
          "Saved field scenarios",
          "Use a preset to reopen a familiar operating pattern without rebuilding the context from scratch.",
          `<div class="space-y-3">
            ${Object.entries(PRESETS)
              .map(
                ([key, preset]) => `
                  <button
                    type="button"
                    data-preset="${key}"
                    class="flex w-full items-start justify-between rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-left transition-all duration-200 hover:border-[var(--accent)] hover:bg-[var(--panel-hover)]"
                  >
                    <div class="pr-4">
                      <p class="text-sm font-medium text-[var(--text)]">${escapeHtml(preset.fieldName)}</p>
                      <p class="mt-1 text-sm text-[var(--text-muted)]">${escapeHtml(preset.analysisPrompt)}</p>
                    </div>
                    <span class="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
                      ${icon("sparkles", "h-4 w-4")}
                    </span>
                  </button>
                `,
              )
              .join("")}
          </div>`,
        )}
      </div>
    </section>
  `;
}
