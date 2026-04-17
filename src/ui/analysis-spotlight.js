import { isLiveApiMode, state } from "../state.js";
import { formatPercent, formatTimestamp, formatWindow, recommendationTone } from "../domain.js";
import { ResultCard } from "./results.js";
import {
  PrimaryButton,
  classNames,
  emptyInspectorState,
  escapeHtml,
  icon,
  inputGroup,
  numericInput,
  selectInput,
} from "./shared.js";

function feedbackSummary(run) {
  if (!run?.regionalInsights) {
    return isLiveApiMode()
      ? "No comparable nearby farmer feedback is being used yet for this field."
      : "Demo mode does not use stored farmer feedback.";
  }
  const yieldText =
    run.regionalInsights.avgYieldDelta == null
      ? "Yield change data is still limited."
      : `Average yield change: ${Number(run.regionalInsights.avgYieldDelta).toFixed(1)}%.`;
  return `${Math.round(run.regionalInsights.successRate * 100)}% success across ${run.regionalInsights.totalSamples} nearby farms within ${Math.round(run.regionalInsights.radiusMiles || 31.07)} miles. Filters require the same crop, soil texture, and irrigation type. ${yieldText}`;
}

function AcknowledgementGate(run) {
  const fieldId = escapeHtml(run.inputSnapshot?.farmId || run.inputSnapshot?.fieldName || "Unknown field");
  const cropType = escapeHtml(run.inputSnapshot?.cropType || "Unknown crop");
  const decision = run.decision === "water" ? "Irrigate Now" : "Hold Irrigation";
  const decisionSubtext = run.decision === "water" ? "Active irrigation call" : "No water needed yet";
  const moisture48h = typeof run.predicted?.moisture48h === "number"
    ? `${(run.predicted.moisture48h * 100).toFixed(1)}% VWC`
    : "—";
  const timingWindow = escapeHtml(formatWindow(run.timingWindow));
  const statTile = (label, value, subtext = "") => `
    <div class="flex flex-col gap-1.5 rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-5 py-4">
      <p class="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${label}</p>
      <p class="text-2xl font-semibold leading-tight tracking-tight text-[var(--text)]">${value}</p>
      ${subtext ? `<p class="text-xs text-[var(--text-muted)]">${subtext}</p>` : ""}
    </div>
  `;

  return `
    <section class="fade-in rounded-[28px] border border-[#d97706]/30 bg-[var(--panel)] shadow-[var(--shadow)]" style="border-left: 5px solid #d97706;">
      <div class="rounded-t-[26px] border-b border-[#d97706]/20 bg-[#d97706]/[0.07] px-7 py-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#d97706]/20">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </span>
            <p class="text-sm font-semibold uppercase tracking-[0.18em]" style="color: #d97706;">Review Required</p>
          </div>
          <span class="rounded-full border border-[#d97706]/30 px-3 py-1 text-xs font-medium" style="color: #d97706; background: rgba(217,119,6,0.08);">Action pending your review</span>
        </div>
        <h3 class="mt-4 text-2xl font-semibold tracking-tight text-[var(--text)] sm:text-3xl">Before You Proceed</h3>
        <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          Read the summary below. When you are satisfied, tap the button to confirm and log your decision.
        </p>
      </div>
      <div class="p-7">
        <div class="grid gap-3 sm:grid-cols-2">
          ${statTile("Field", fieldId, "Active field")}
          ${statTile("Crop Type", cropType.charAt(0).toUpperCase() + cropType.slice(1), "Current season")}
          ${statTile("Irrigation Decision", decision, decisionSubtext)}
          ${statTile("48h Moisture Forecast", moisture48h, timingWindow ? `Window: ${timingWindow}` : "Forecasted soil VWC")}
        </div>
        <div class="mt-8">
          <button
            type="button"
            id="acknowledge-proceed-btn"
            class="flex w-full items-center justify-center gap-3 rounded-2xl px-6 py-5 text-base font-semibold tracking-tight text-white shadow-lg transition-all duration-150 hover:brightness-110 active:scale-[0.985]"
            style="background: linear-gradient(135deg, #d97706, #b45309); box-shadow: 0 8px 32px rgba(217,119,6,0.28);"
          >
            <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m5 13 4 4L19 7"/>
            </svg>
            I've reviewed this — proceed
          </button>
          <p class="mt-3 text-center text-xs text-[var(--text-muted)]">This action will be logged with a timestamp.</p>
        </div>
      </div>
    </section>
  `;
}

export function RecommendationSpotlight() {
  if (state.acknowledgement.pendingRun) {
    return AcknowledgementGate(state.acknowledgement.pendingRun);
  }
  if (!state.latestRun) {
    return `
      <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation</p>
            <h3 class="mt-2 text-xl font-semibold text-[var(--text)]">Run an analysis to reveal the irrigation call</h3>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
              The result will surface here with the recommended amount, timing window, heuristic confidence, and the main drivers behind the estimate.
            </p>
          </div>
          <span class="hidden rounded-full bg-[var(--accent-soft)] px-4 py-2 text-xs font-medium text-[var(--accent)] lg:inline-flex">
            Waiting for first run
          </span>
        </div>
      </section>
    `;
  }

  const run = state.latestRun;
  const tone = recommendationTone(run);
  return `
    <section class="accent-divider rounded-[28px] border p-6 shadow-[var(--shadow)] ${tone.spotlight}">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="max-w-2xl">
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommendation</p>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <h3 class="text-[28px] font-semibold tracking-tight text-[var(--text)]">${run.decision === "water" ? "Irrigate now" : "Hold irrigation"}</h3>
            <span class="rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${tone.pill}">
              ${run.decision.toUpperCase()}
            </span>
          </div>
          <p class="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-right">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Latest run</p>
          <p class="mt-2 text-sm font-medium text-[var(--text)]">${formatTimestamp(run.timestamp)}</p>
        </div>
      </div>
      <div class="mt-6 grid gap-4 lg:grid-cols-[1.2fr_repeat(3,minmax(0,1fr))]">
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Recommended amount</p>
          <div class="mt-3 flex items-end gap-3">
            <span class="text-5xl font-semibold tracking-tight ${tone.amount}">${(run.recommendedAmountIn ?? 0).toFixed(2)}</span>
            <span class="pb-1 text-lg font-medium text-[var(--text-muted)]">in</span>
          </div>
          <p class="mt-4 text-sm text-[var(--text-muted)]">This is the number the operator should notice first.</p>
          ${run.bindingConstraint ? `<p class="mt-2 text-xs text-[var(--text-muted)]">Limited by: ${escapeHtml({ need: "Water deficit", maxVolume: "System volume limit", pumpCapacity: "Pump throughput", budget: "Budget cap", infiltration: "Infiltration rate" }[run.bindingConstraint] || run.bindingConstraint)}</p>` : ""}
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Best timing</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${escapeHtml(formatWindow(run.timingWindow))}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Heuristic confidence</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${formatPercent(run.confidenceScore)}</p>
        </div>
        <div class="rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
          <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Stress risk</p>
          <p class="mt-4 text-2xl font-semibold text-[var(--text)]">${formatPercent(run.stressProbability)}</p>
        </div>
      </div>
      <div class="mt-4 rounded-3xl border border-[var(--border)] bg-[var(--panel)] p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">Farmer feedback</p>
            <p class="mt-2 text-sm text-[var(--text-muted)]">${escapeHtml(feedbackSummary(run))}</p>
            ${run.sourceLabel ? `<p class="mt-2 text-sm text-[var(--text-muted)]">Source: ${escapeHtml(run.sourceLabel)}</p>` : ""}
            ${run.recommendationAdjustment ? `<p class="mt-2 text-sm text-[var(--text-muted)]">Adjustment reason: ${escapeHtml(run.recommendationAdjustment.reason)}</p>` : ""}
          </div>
          <button
            type="button"
            id="feedback-toggle"
            class="inline-flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)]"
          >
            Submit Feedback
          </button>
        </div>
        ${state.feedbackForm.open ? `
          <div class="mt-4 grid gap-4 sm:grid-cols-2">
            ${inputGroup("Did this recommendation work?", selectInput("feedbackOutcome", state.feedbackForm.outcome, [
              { value: "SUCCESS", label: "Success" },
              { value: "PARTIAL", label: "Partial" },
              { value: "FAILURE", label: "Failure" },
            ]))}
            ${inputGroup("Yield change (%)", numericInput("feedbackYieldDelta", state.feedbackForm.yieldDelta, "-100", "0.1", "1000"))}
          </div>
          <div class="mt-4">
            ${inputGroup("Notes", `<textarea id="feedback-notes" class="min-h-[96px] w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]">${escapeHtml(state.feedbackForm.notes)}</textarea>`)}
          </div>
          ${!isLiveApiMode() ? `<p class="mt-3 text-xs text-[var(--text-muted)]">Your feedback is stored locally and will be sent when the backend is available.</p>` : ""}
          <div class="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              id="feedback-submit"
              class="inline-flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200 hover:border-[var(--accent)]"
            >
              ${state.feedbackForm.submitting ? "Submitting..." : "Send"}
            </button>
            ${state.feedbackForm.error ? `<p class="text-sm text-[var(--accent-warm)]">${escapeHtml(state.feedbackForm.error)}</p>` : ""}
            ${state.feedbackForm.status ? `<p class="text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
          </div>
        ` : state.feedbackForm.status ? `<p class="mt-4 text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
      </div>
    </section>
    <p style="font-size: 0.85rem; font-style: italic; color: var(--text-muted); margin-top: 0.75rem;">This is decision support. Review with your own judgment before acting on any recommendation.</p>
  `;
}

export function AnalysisConsoleDisclosure() {
  const expanded = state.analysisConsoleOpen;
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-3 shadow-[var(--shadow)]">
      <button
        type="button"
        id="analysis-console-toggle"
        aria-expanded="${expanded ? "true" : "false"}"
        aria-controls="analysis-console-panel"
        class="flex w-full items-center justify-between gap-4 rounded-[22px] px-3 py-3 text-left transition-all duration-200 hover:bg-[var(--panel-muted)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <div>
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Analysis Console</p>
          <p class="mt-2 text-sm text-[var(--text-muted)]">
            Open recent runs, copyable analysis details, and technical output when you need deeper review.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <span class="hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)] sm:inline-flex">
            ${state.runHistory.length} stored
          </span>
          <span class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] text-[var(--text-muted)]">
            <span class="transition-transform duration-200 ${expanded ? "rotate-180" : ""}">
              ${icon("chevronDown", "h-5 w-5")}
            </span>
          </span>
        </div>
      </button>
      <div
        id="analysis-console-panel"
        aria-hidden="${expanded ? "false" : "true"}"
        ${expanded ? "" : "inert"}
        class="${classNames(
          "grid overflow-hidden transition-all duration-300 ease-out",
          expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}"
      >
        <div class="min-h-0">
          <div class="border-t border-[var(--border)] px-3 pb-3 pt-4">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="text-lg font-medium text-[var(--text)]">Recent analysis runs</h2>
                <p class="mt-1 text-sm text-[var(--text-muted)]">Technical details stay available here without interrupting the main decision flow.</p>
              </div>
              <div class="flex items-center gap-2">
                ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
                <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)]">
                  ${state.runHistory.length} total
                </div>
              </div>
            </div>
            <div class="mt-4 space-y-3">
              ${state.runHistory.length > 0
                ? state.runHistory.slice(0, 8).map((run) => ResultCard(run, true)).join("")
                : emptyInspectorState()}
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}
