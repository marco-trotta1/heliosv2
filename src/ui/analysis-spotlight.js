import { isLiveApiMode, state } from "../state.js";
import { formatWindow } from "../domain.js";
import { ResultCard } from "./results.js";
import { RecommendationHero } from "./dashboard.js";
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
  if (run?.backendSnapshot?.validationMode) {
    return "Validation mode disabled nearby-farmer feedback so researchers can score this recommendation cleanly.";
  }
  if (!run?.regionalInsights) {
    return isLiveApiMode()
      ? "No nearby farmer feedback yet."
      : "Demo mode does not use stored farmer feedback.";
  }

  const yieldText =
    run.regionalInsights.avgYieldDelta == null
      ? "Yield data is limited."
      : `Average yield change: ${Number(run.regionalInsights.avgYieldDelta).toFixed(1)}%.`;

  return `${Math.round(run.regionalInsights.successRate * 100)}% success across ${run.regionalInsights.totalSamples} nearby farms within ${Math.round(run.regionalInsights.radiusMiles || 31.07)} miles. ${yieldText}`;
}

function zoneSpread(run) {
  const values = Object.values(run.zoneMoistureSummary || {}).map(Number).filter((value) => Number.isFinite(value));
  if (values.length < 2) {
    return null;
  }
  return Math.max(...values) - Math.min(...values);
}

function zoneSummary(run) {
  const entries = Object.entries(run.zoneMoistureSummary || {});
  if (entries.length === 0) {
    return "Only one probe summary was available for this run.";
  }
  return entries
    .map(([sensorId, moisture]) => `${sensorId}: ${(Number(moisture) * 100).toFixed(1)}%`)
    .join(" • ");
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

function contextRow(label, value) {
  return `
    <div class="flex items-center justify-between gap-3 border-b border-dashed border-[var(--hairline)] py-2.5 last:border-b-0">
      <span class="eyebrow-muted">${label}</span>
      <span class="num text-[13px] font-extrabold tracking-[0.04em] text-[var(--ink)] text-right truncate max-w-[60%]">${value}</span>
    </div>
  `;
}

function ValidationBanner(run) {
  const hash = run.backendSnapshot?.modelHash ? escapeHtml(String(run.backendSnapshot.modelHash)) : "—";
  const trainedAt = run.backendSnapshot?.trainedAt ? escapeHtml(String(run.backendSnapshot.trainedAt)) : "";
  return `
    <section class="validation-banner">
      <div>
        <p class="eyebrow" style="color: var(--accent-warm);">VALIDATION BUILD</p>
        <p class="mt-1.5 text-sm leading-6 text-[var(--text)]">Nearby-farmer feedback is disabled so researchers can score this recommendation cleanly against field observations.</p>
      </div>
      <div class="num shrink-0 text-[11px] font-extrabold tracking-[0.12em] text-[var(--text-muted)] text-right">
        <div>BUILD · ${hash}</div>
        ${trainedAt ? `<div class="mt-1">TRAINED · ${trainedAt}</div>` : ""}
      </div>
    </section>
  `;
}

function AcknowledgementGate(run) {
  const fieldId = escapeHtml(run.inputSnapshot?.farmId || run.inputSnapshot?.fieldName || "Unknown field");
  const cropType = escapeHtml(run.inputSnapshot?.cropType || "Unknown crop");
  const decision = run.decision === "water" ? "IRRIGATE NOW" : "HOLD IRRIGATION";
  const moisture48h = typeof run.predicted?.moisture48h === "number"
    ? `${(run.predicted.moisture48h * 100).toFixed(1)}% VWC`
    : "—";

  return `
    <section class="fade-in validation-banner flex-col items-stretch gap-4">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="eyebrow" style="color: var(--accent-warm);">REVIEW REQUIRED</p>
          <p class="mt-1.5 text-base font-semibold text-[var(--ink)]">Confirm the recommendation before you proceed.</p>
        </div>
      </div>
      <div class="grid gap-0 rounded-[10px] border border-[var(--hairline)] bg-[var(--panel)] px-4 py-2">
        ${contextRow("FIELD", fieldId)}
        ${contextRow("CROP", cropType.toUpperCase())}
        ${contextRow("DECISION", decision)}
        ${contextRow("48H FORECAST", moisture48h)}
        ${contextRow("WINDOW", escapeHtml(formatWindow(run.timingWindow)).toUpperCase())}
      </div>
      <button
        type="button"
        id="acknowledge-proceed-btn"
        class="focus-outline flex min-h-[52px] w-full items-center justify-center gap-2 rounded-[8px] bg-[var(--ink)] px-5 py-3 text-xs font-extrabold tracking-[0.2em] text-[var(--amber)] shadow-[0_10px_26px_-10px_rgba(24,38,29,0.55)] transition-all duration-150 hover:brightness-110 active:scale-[0.99]"
      >
        <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m5 13 4 4L19 7"/>
        </svg>
        <span>I'VE REVIEWED THIS — PROCEED</span>
      </button>
    </section>
  `;
}

function ContextPanel(run) {
  const spread = zoneSpread(run);
  const constraintHtml = run.bindingConstraint
    ? contextRow("LIMITED BY", escapeHtml(bindingConstraintLabel(run.bindingConstraint)).toUpperCase())
    : "";
  const zoneLabel = run.drivingZone ? escapeHtml(String(run.drivingZone).toUpperCase()) : "UNAVAILABLE";
  const spreadLabel = spread == null ? "SINGLE PROBE" : `${(spread * 100).toFixed(1)} PTS`;
  const variabilityHtml = run.highVariabilityFlag
    ? `<p class="mt-2 text-[12px] leading-5 text-[var(--accent-warm)]">High spatial variability detected across probe readings.</p>`
    : "";

  return `
    <section class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)]">
      <div class="flex items-center justify-between">
        <p class="eyebrow">FIELD CONTEXT</p>
        <span class="num text-[10px] font-bold tracking-[0.12em] text-[var(--text-muted)]">LATEST RUN</span>
      </div>
      <div class="mt-3 grid gap-0">
        ${contextRow("DRIVING ZONE", zoneLabel)}
        ${contextRow("ZONE SPREAD", spreadLabel)}
        ${constraintHtml}
      </div>
      ${zoneSummary(run) ? `<p class="num mt-3 text-[11px] leading-5 text-[var(--text-muted)]">${escapeHtml(zoneSummary(run))}</p>` : ""}
      ${variabilityHtml}
    </section>
  `;
}

function FeedbackPanel(run) {
  const isValidation = run.backendSnapshot?.validationMode === true;
  const heading = isValidation ? "VALIDATION CONTEXT" : "NEARBY FEEDBACK";

  return `
    <section class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)]">
      <p class="eyebrow">${heading}</p>
      <p class="mt-3 text-[13px] leading-6 text-[var(--text-muted)]">${escapeHtml(feedbackSummary(run))}</p>
      ${isValidation ? "" : `
        <div class="mt-4 border-t border-dashed border-[var(--hairline)] pt-4">
          <button
            type="button"
            id="feedback-toggle"
            class="focus-outline inline-flex items-center justify-center rounded-[8px] border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs font-extrabold tracking-[0.14em] text-[var(--ink)] transition-all duration-200 hover:border-[var(--border-strong)]"
          >
            ${state.feedbackForm.open ? "HIDE FEEDBACK FORM" : "SUBMIT FEEDBACK"}
          </button>
          ${state.feedbackForm.open ? `
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              ${inputGroup("Did this recommendation work?", selectInput("feedbackOutcome", state.feedbackForm.outcome, [
                { value: "SUCCESS", label: "Success" },
                { value: "PARTIAL", label: "Partial" },
                { value: "FAILURE", label: "Failure" },
              ]))}
              ${inputGroup("Yield change (%)", numericInput("feedbackYieldDelta", state.feedbackForm.yieldDelta, "-100", "0.1", "1000"))}
            </div>
            <div class="mt-3">
              ${inputGroup("Notes", `<textarea id="feedback-notes" class="focus-outline min-h-[96px] w-full rounded-[10px] border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]">${escapeHtml(state.feedbackForm.notes)}</textarea>`)}
            </div>
            <div class="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                id="feedback-submit"
                class="focus-outline inline-flex items-center justify-center rounded-[8px] bg-[var(--ink)] px-3.5 py-2 text-xs font-extrabold tracking-[0.2em] text-[var(--amber)] transition-all duration-200 hover:brightness-110"
              >
                ${state.feedbackForm.submitting ? "SUBMITTING..." : "SEND FEEDBACK"}
              </button>
              ${state.feedbackForm.error ? `<p class="text-xs text-[var(--accent-warm)]">${escapeHtml(state.feedbackForm.error)}</p>` : ""}
              ${state.feedbackForm.status ? `<p class="text-xs text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
            </div>
          ` : state.feedbackForm.status ? `<p class="mt-3 text-xs text-[var(--text-muted)]">${escapeHtml(state.feedbackForm.status)}</p>` : ""}
        </div>
      `}
    </section>
  `;
}

export function RecommendationSpotlight() {
  if (state.acknowledgement.pendingRun) {
    return AcknowledgementGate(state.acknowledgement.pendingRun);
  }

  if (!state.latestRun) {
    return RecommendationHero(null);
  }

  const run = state.latestRun;
  const isValidation = run.backendSnapshot?.validationMode === true;

  return `
    <div class="fade-in space-y-5">
      ${isValidation ? ValidationBanner(run) : ""}
      ${RecommendationHero(run, { showRunButton: false })}
      <div class="grid gap-5 xl:grid-cols-2">
        ${ContextPanel(run)}
        ${FeedbackPanel(run)}
      </div>
    </div>
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
