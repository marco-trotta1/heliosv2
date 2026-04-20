import { PRESETS } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow, recommendationTone } from "../domain.js";
import { state, runtimeConfig } from "../state.js";
import { emptyBlock, escapeHtml, icon } from "./shared.js";

function dashboardRunItem(run) {
  const decisionPillClass = run.decision === "water" ? "pill-water" : "pill-wait";

  return `
    <article class="fade-in rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 shadow-[var(--shadow)]">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">${formatTimestamp(run.timestamp)}</p>
          <p class="mt-2 text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">${escapeHtml(run.inputSnapshot.fieldName)}</p>
          <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="shrink-0 text-right">
          <span class="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] ${decisionPillClass}">${run.decision.toUpperCase()}</span>
          <p class="mt-3 text-2xl font-semibold tracking-[-0.04em] ${run.decision === "water" ? "tone-water" : "tone-wait"}">${(run.recommendedAmountIn ?? 0).toFixed(2)}<span class="ml-1 text-sm font-semibold text-[var(--text-muted)]">in</span></p>
        </div>
      </div>
    </article>
  `;
}

function DashboardMetric(label, value, hint) {
  return `
    <div class="rounded-[26px] border border-[var(--border)] bg-[var(--panel)] px-5 py-5 shadow-[var(--shadow)]">
      <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">${label}</p>
      <p class="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">${value}</p>
      <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">${hint}</p>
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
          hint: "Secondary signal for the current recommendation.",
        },
        {
          label: "Stress risk",
          value: formatPercent(latestRun.stressProbability),
          hint: "Estimated crop stress if the field waits.",
        },
        {
          label: "Best window",
          value: escapeHtml(formatWindow(latestRun.timingWindow)),
          hint: "Preferred operating window from the latest run.",
        },
      ]
    : [
        {
          label: "Recent runs",
          value: `${totalRuns}`,
          hint: "Analyses currently available in local history.",
        },
        {
          label: "Saved runs",
          value: `${savedRuns}`,
          hint: "Pinned scenarios ready for quick review.",
        },
        {
          label: "Workspace mode",
          value: runtimeConfig.mode === "live" ? "Live API" : "Demo mode",
          hint: "Current workspace mode.",
        },
      ];

  return `
    <section class="rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)]">
      <div class="pb-4">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Today at a glance</p>
      </div>
      <div class="grid gap-3 md:grid-cols-3">
        ${metrics.map((metric) => DashboardMetric(metric.label, metric.value, metric.hint)).join("")}
      </div>
    </section>
  `;
}

function DashboardSection(eyebrow, title, body, content, action = "") {
  return `
    <section class="rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="max-w-2xl">
          <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">${eyebrow}</p>
          <h3 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[var(--text)]">${title}</h3>
          ${body ? `<p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">${body}</p>` : ""}
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
      <section class="surface-ring rounded-[34px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow-strong)]">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Current field status</p>
        <div class="mt-4 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div class="max-w-3xl">
            <h2 class="text-[38px] font-semibold tracking-[-0.05em] text-[var(--text)]">No recent irrigation recommendation</h2>
          </div>
          <button
            type="button"
            data-nav="run-analysis"
            class="focus-outline inline-flex min-h-[54px] items-center gap-2 rounded-[22px] bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow)] transition-all duration-200 hover:bg-[var(--accent-hover)]"
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
  const decisionPillClass = run.decision === "water" ? "pill-water" : "pill-wait";

  return `
    <section class="surface-ring accent-divider rounded-[34px] border p-6 shadow-[var(--shadow-strong)] ${tone.spotlight}">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] xl:items-end">
        <div class="max-w-3xl">
          <div class="flex flex-wrap items-center gap-3">
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Current field status</p>
            <span class="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] ${decisionPillClass}">
              ${run.decision === "water" ? "Water now" : "Hold"}
            </span>
          </div>
          <h2 class="mt-4 text-[38px] font-semibold tracking-[-0.05em] text-[var(--text)]">${run.decision === "water" ? `Apply ${(run.recommendedAmountIn ?? 0).toFixed(2)} in ${escapeHtml(formatWindow(run.timingWindow)).toLowerCase()}` : "Hold irrigation for now"}</h2>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
          <div class="rounded-[26px] border border-[var(--border)] bg-[var(--panel)] px-4 py-4 shadow-[var(--shadow)]">
            <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Most recent field</p>
            <p class="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "Untitled field")}</p>
            <p class="mt-2 text-sm text-[var(--text-muted)]">${formatTimestamp(run.timestamp)}</p>
          </div>
          <button
            type="button"
            data-nav="run-analysis"
            class="focus-outline inline-flex items-center justify-center gap-2 rounded-[26px] border border-[var(--border)] bg-[var(--panel)] px-4 py-4 text-sm font-semibold text-[var(--text)] shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--border-strong)]"
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
          "Recent activity",
          "Latest field decisions",
          "",
          `<div class="space-y-3">
            ${state.runHistory.slice(0, 3).map((run) => dashboardRunItem(run)).join("") || emptyBlock("No runs yet", "Start with Run Analysis to populate the dashboard feed.")}
          </div>`,
          `<button
            type="button"
            data-nav="run-analysis"
            class="focus-outline inline-flex items-center gap-2 rounded-[20px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-2.5 text-sm font-semibold text-[var(--text)] transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--panel)]"
          >
            ${icon("sparkles", "h-4 w-4")}
            <span>New analysis</span>
          </button>`,
        )}
        ${DashboardSection(
          "Quick start",
          "Saved field scenarios",
          "",
          `<div class="space-y-3">
            ${Object.entries(PRESETS)
              .map(
                ([key, preset]) => `
                  <button
                    type="button"
                    data-preset="${key}"
                    class="focus-outline flex w-full items-start justify-between rounded-[28px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-left shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--panel)]"
                  >
                    <div class="pr-4">
                      <p class="text-sm font-semibold text-[var(--text)]">${escapeHtml(preset.fieldName)}</p>
                      <p class="mt-1 text-sm leading-6 text-[var(--text-muted)]">${escapeHtml(preset.analysisPrompt)}</p>
                    </div>
                    <span class="mt-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] bg-[var(--accent-soft)] text-[var(--accent)]">
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
