import { isLiveApiMode, state } from "../state.js";
import { formatPercent, formatTimestamp, formatWindow, recommendationTone } from "../domain.js";
import { ResultCard } from "./results.js";
import {
  PrimaryButton,
  classNames,
  emptyInspectorState,
  escapeHtml,
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

function summarySentence(run) {
  if (run.decision === "water") {
    return `Apply ${(run.recommendedAmountIn ?? 0).toFixed(2)} in during ${formatWindow(run.timingWindow).toLowerCase()}.`;
  }
  return `Hold irrigation and review ${formatWindow(run.timingWindow).toLowerCase()} as the next best operating window.`;
}

function bindingConstraintLabel(value) {
  return {
    need: "Water deficit",
    maxVolume: "System volume limit",
    pumpCapacity: "Pump throughput",
    budget: "Budget cap",
    infiltration: "Infiltration rate",
  }[value] || value;
}

function statTile(label, value, helper = "", emphasisClass = "") {
  return `
    <div class="rounded-[24px] border border-[var(--border)] bg-[var(--panel)] px-4 py-4 shadow-[var(--shadow)]">
      <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">${label}</p>
      <p class="${classNames("mt-3 text-2xl font-semibold tracking-[-0.03em] text-[var(--text)]", emphasisClass)}">${value}</p>
      ${helper ? `<p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">${helper}</p>` : ""}
    </div>
  `;
}

function AcknowledgementGate(run) {
  const fieldId = escapeHtml(run.inputSnapshot?.farmId || run.inputSnapshot?.fieldName || "Unknown field");
  const cropType = escapeHtml(run.inputSnapshot?.cropType || "Unknown crop");
  const decision = run.decision === "water" ? "Irrigate now" : "Hold irrigation";
  const moisture48h = typeof run.predicted?.moisture48h === "number"
    ? `${(run.predicted.moisture48h * 100).toFixed(1)}% VWC`
    : "—";

  return `
    <section class="fade-in surface-ring rounded-[32px] border border-[var(--accent-warm-soft)] bg-[var(--panel)] p-6 shadow-[var(--shadow-strong)]">
      <div class="rounded-[26px] border border-[var(--accent-warm-soft)] bg-[var(--accent-warm-soft)] px-5 py-5">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent-warm)]">Review Required</p>
        <h3 class="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">Confirm the recommendation before you proceed</h3>
        <p class="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">The decision has been prepared for this field. Review the essentials below, then acknowledge to log the action.</p>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        ${statTile("Field", fieldId, "Active field")}
        ${statTile("Crop", cropType.charAt(0).toUpperCase() + cropType.slice(1), "Current season")}
        ${statTile("Decision", decision, "Farmer-facing call")}
        ${statTile("48h Forecast", moisture48h, formatWindow(run.timingWindow))}
      </div>

      <div class="mt-6">
        <button
          type="button"
          id="acknowledge-proceed-btn"
          class="focus-outline flex min-h-[60px] w-full items-center justify-center gap-3 rounded-[24px] bg-[var(--accent-warm)] px-6 py-5 text-base font-semibold text-white shadow-[var(--shadow)] transition-all duration-150 hover:brightness-105 active:scale-[0.99]"
        >
          <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m5 13 4 4L19 7"/>
          </svg>
          <span>I’ve reviewed this — proceed</span>
        </button>
        <p class="mt-3 text-center text-xs text-[var(--text-muted)]">This acknowledgement is logged with a timestamp.</p>
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
      <section class="surface-ring rounded-[32px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow-strong)]">
        <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl">
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Current Recommendation</p>
            <h3 class="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">Run an analysis to reveal the irrigation call</h3>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">The decision card will appear here with the recommended amount, timing window, confidence, and the main supporting drivers.</p>
          </div>
          <span class="inline-flex rounded-full bg-[var(--accent-soft)] px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--accent)]">
            Waiting for first run
          </span>
        </div>
      </section>
    `;
  }

  const run = state.latestRun;
  const tone = recommendationTone(run);
  const decisionLabel = run.decision === "water" ? "Irrigate now" : "Hold irrigation";
  const decisionPillClass = run.decision === "water" ? "pill-water" : "pill-wait";
  const amountClass = run.decision === "water" ? "tone-water" : "tone-wait";

  return `
    <section class="fade-in accent-divider surface-ring rounded-[32px] border p-6 shadow-[var(--shadow-strong)] ${tone.spotlight}">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <div>
          <div class="flex flex-wrap items-center gap-3">
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Current Recommendation</p>
            <span class="rounded-full px-3 py-1.5 text-xs font-bold uppercase tracking-[0.18em] ${decisionPillClass}">
              ${run.decision.toUpperCase()}
            </span>
          </div>
          <h3 class="mt-3 text-[38px] font-semibold tracking-[-0.05em] text-[var(--text)]">${decisionLabel}</h3>
          <p class="mt-3 max-w-2xl text-base leading-8 text-[var(--text-muted)]">${escapeHtml(summarySentence(run))}</p>
          <p class="mt-2 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">${escapeHtml(run.summary)}</p>

          <div class="mt-6 grid gap-4 sm:grid-cols-2">
            <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] px-5 py-5 shadow-[var(--shadow)]">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">Recommended amount</p>
              <div class="mt-3 flex items-end gap-3">
                <span class="text-6xl font-semibold tracking-[-0.06em] ${amountClass}">${(run.recommendedAmountIn ?? 0).toFixed(2)}</span>
                <span class="pb-2 text-lg font-semibold text-[var(--text-muted)]">in</span>
              </div>
              ${run.bindingConstraint ? `<p class="mt-3 text-sm leading-6 text-[var(--text-muted)]">Limited by ${escapeHtml(bindingConstraintLabel(run.bindingConstraint))}.</p>` : `<p class="mt-3 text-sm leading-6 text-[var(--text-muted)]">The primary number for the operator to notice first.</p>`}
            </div>
            <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] px-5 py-5 shadow-[var(--shadow)]">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">Best timing window</p>
              <p class="mt-4 text-3xl font-semibold tracking-[-0.04em] text-[var(--text)]">${escapeHtml(formatWindow(run.timingWindow))}</p>
              <p class="mt-3 text-sm leading-6 text-[var(--text-muted)]">Use this as the preferred operating window for the next pass.</p>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          ${statTile("Latest run", formatTimestamp(run.timestamp), "Most recent field decision")}
          <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            ${statTile("Heuristic confidence", formatPercent(run.confidenceScore), "Useful context, secondary to the irrigation call.")}
            ${statTile("Stress risk", formatPercent(run.stressProbability), "Estimated crop stress if the field waits.")}
          </div>
          <div class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] px-5 py-5 shadow-[var(--shadow)]">
            <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--text-muted)]">Farmer feedback</p>
            <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">${escapeHtml(feedbackSummary(run))}</p>
            ${run.sourceLabel ? `<p class="mt-3 text-sm text-[var(--text-muted)]">Source: ${escapeHtml(run.sourceLabel)}</p>` : ""}
            ${run.recommendationAdjustment ? `<p class="mt-2 text-sm text-[var(--text-muted)]">Adjustment reason: ${escapeHtml(run.recommendationAdjustment.reason)}</p>` : ""}
            <div class="mt-4 border-t border-[var(--border)] pt-4">
              <button
                type="button"
                id="feedback-toggle"
                class="focus-outline inline-flex items-center justify-center rounded-[18px] border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-2.5 text-sm font-semibold text-[var(--text)] transition-all duration-200 hover:border-[var(--border-strong)]"
              >
                Submit feedback
              </button>
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
                  ${inputGroup("Notes", `<textarea id="feedback-notes" class="focus-outline min-h-[108px] w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-3 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]">${escapeHtml(state.feedbackForm.notes)}</textarea>`)}
                </div>
                ${!isLiveApiMode() ? `<p class="mt-3 text-xs text-[var(--text-muted)]">Your feedback is stored locally and will be sent when the backend is available.</p>` : ""}
                <div class="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    id="feedback-submit"
                    class="focus-outline inline-flex items-center justify-center rounded-[18px] border border-[var(--accent)] bg-[var(--accent)] px-3.5 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-[var(--accent-hover)]"
                  >
                    ${state.feedbackForm.submitting ? "Submitting..." : "Send feedback"}
                  </button>
                  ${state.feedbackForm.error ? `<p class="text-sm text-[var(--accent-warm)]">${escapeHtml(state.feedbackForm.error)}</p>` : ""}
                  ${state.feedbackForm.status ? `<p class="text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
                </div>
              ` : state.feedbackForm.status ? `<p class="mt-4 text-sm text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
            </div>
          </div>
        </div>
      </div>
      <p class="mt-4 text-xs leading-6 text-[var(--text-muted)]">Helios is decision support. Review the recommendation with your own field judgment before acting.</p>
    </section>
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
        class="focus-outline flex w-full items-center justify-between gap-4 rounded-[22px] px-4 py-4 text-left transition-all duration-200 hover:bg-[var(--panel-muted)]"
      >
        <div>
          <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">Technical Details</p>
          <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">Open recent runs, copyable details, and the underlying analysis output when a deeper review is needed.</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="hidden rounded-full border border-[var(--border)] bg-[var(--panel)] px-3 py-1.5 text-xs font-semibold text-[var(--text-muted)] sm:inline-flex">
            ${state.runHistory.length} stored
          </span>
          <span class="inline-flex h-10 w-10 items-center justify-center rounded-[18px] border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] shadow-[var(--shadow)]">
            <span class="transition-transform duration-200 ${expanded ? "rotate-180" : ""}">
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="m6 9 6 6 6-6"/>
              </svg>
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
          <div class="border-t border-[var(--border)] px-4 pb-4 pt-4">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 class="text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">Recent analysis runs</h2>
                <p class="mt-1 text-sm text-[var(--text-muted)]">Technical output stays available here without crowding the main decision surface.</p>
              </div>
              <div class="flex items-center gap-2">
                ${state.latestRun ? PrimaryButton({ id: "save-latest-run", label: "Save latest", iconName: "bookmark", variant: "secondary", extraClass: "px-3 py-2 text-xs" }) : ""}
                <div class="rounded-full border border-[var(--border)] bg-[var(--panel)] px-3 py-1.5 text-xs font-semibold text-[var(--text-muted)]">
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
