import { PRESETS } from "../constants.js";
import { formatPercent, formatTimestamp, formatWindow } from "../domain.js";
import { state } from "../state.js";
import {
  confidenceBar,
  decisionPill,
  escapeHtml,
  etSourceTag,
  icon,
} from "./shared.js";

function dashboardRunItem(run, isLast = false) {
  const isValidation = run.backendSnapshot?.validationMode === true;
  const meta = run.summary
    ? escapeHtml(run.summary).split(".")[0]
    : `${formatPercent(run.confidenceScore)} conf · ${(run.recommendedAmountIn ?? 0).toFixed(2)} in`;

  return `
    <div class="fade-in flex items-center justify-between gap-4 px-4 py-3 ${isLast ? "" : "border-b border-dashed border-[var(--hairline)]"}">
      <div class="flex min-w-0 items-center gap-3">
        ${decisionPill(run.decision)}
        <span class="num text-sm font-extrabold tracking-[0.02em] text-[var(--text)]">${escapeHtml(run.inputSnapshot?.fieldName || "UNTITLED")}</span>
        <span class="text-xs text-[var(--text-muted)] font-semibold">${formatTimestamp(run.timestamp)}</span>
        ${isValidation ? `<span class="num text-[9px] font-extrabold tracking-[0.18em] px-1.5 py-0.5 rounded bg-[var(--accent-warm-soft)] text-[var(--accent-warm)]">VALIDATION</span>` : ""}
      </div>
      <div class="num shrink-0 text-xs font-bold text-[var(--text-muted)] text-right truncate max-w-[240px]">${meta}</div>
    </div>
  `;
}

function DashboardMetrics() {
  const latestRun = state.latestRun;

  const soilMoisturePct = latestRun && typeof latestRun.inputSnapshot?.currentMoisture === "number"
    ? Math.round(latestRun.inputSnapshot.currentMoisture * 100)
    : null;
  const lagMoisturePct = latestRun && typeof latestRun.inputSnapshot?.lagOneMoisture === "number"
    ? Math.round(latestRun.inputSnapshot.lagOneMoisture * 100)
    : null;
  const moistureDelta = soilMoisturePct != null && lagMoisturePct != null
    ? soilMoisturePct - lagMoisturePct
    : null;

  const etValue = latestRun && typeof latestRun.estimatedEtIn === "number" && latestRun.estimatedEtIn > 0
    ? latestRun.estimatedEtIn.toFixed(2)
    : "—";

  const precipIn = latestRun && typeof latestRun.inputSnapshot?.precipitationIn === "number"
    ? latestRun.inputSnapshot.precipitationIn
    : null;

  const soilSourceHtml = latestRun && soilMoisturePct != null
    ? `<span class="num text-[9px] font-bold tracking-[0.12em] text-[var(--text-muted)]">LATEST</span>`
    : `<span class="num text-[9px] font-bold tracking-[0.12em] text-[var(--text-muted)]">—</span>`;

  const soilDeltaHtml = moistureDelta == null
    ? `<p class="mt-3 num text-[11px] font-bold text-[var(--text-muted)]">No prior reading</p>`
    : moistureDelta >= 0
      ? `<p class="mt-3 num text-[11px] font-extrabold text-[var(--accent)]">▲ ${Math.abs(moistureDelta).toFixed(1)} pts / 6H</p>`
      : `<p class="mt-3 num text-[11px] font-extrabold text-[var(--accent-warm)]">▼ ${Math.abs(moistureDelta).toFixed(1)} pts / 6H</p>`;

  const etFooter = latestRun
    ? `<p class="mt-3 num text-[11px] font-bold text-[var(--text-muted)]">${latestRun.etSource === "openet-live" || latestRun.etSource === "openet-cache" ? "live monthly point" : "monthly estimate"}</p>`
    : `<p class="mt-3 num text-[11px] font-bold text-[var(--text-muted)]">awaiting run</p>`;

  const rainValue = precipIn != null && precipIn > 0
    ? precipIn.toFixed(2)
    : "0.00";
  const rainFooter = precipIn != null && precipIn > 0
    ? `<p class="mt-3 num text-[11px] font-bold text-[var(--text-muted)]">in forecast</p>`
    : `<p class="mt-3 num text-[11px] font-bold text-[var(--text-muted)]">none forecast</p>`;

  return `
    <section>
      <div class="grid gap-3 md:grid-cols-3">
        <div class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-5 rail-warm shadow-[var(--shadow)]">
          <div class="flex items-center justify-between">
            <p class="eyebrow">SOIL MOISTURE</p>
            ${soilSourceHtml}
          </div>
          <div class="mt-4 flex items-baseline gap-2">
            <span class="num" style="font-size: 60px; font-weight: 800; line-height: 0.85; color: var(--text); letter-spacing: -0.03em;">${soilMoisturePct ?? "—"}</span>
            <span class="num" style="font-size: 18px; font-weight: 700; color: var(--text-muted);">%</span>
          </div>
          ${soilDeltaHtml}
        </div>
        <div class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-5 rail-forest shadow-[var(--shadow)]">
          <div class="flex items-center justify-between">
            <p class="eyebrow">ET · LATEST</p>
            ${latestRun ? etSourceTag(latestRun.etSource) : `<span class="num text-[9px] font-bold tracking-[0.12em] text-[var(--text-muted)]">—</span>`}
          </div>
          <div class="mt-4 flex items-baseline gap-2">
            <span class="num" style="font-size: 60px; font-weight: 800; line-height: 0.85; color: var(--text); letter-spacing: -0.03em;">${etValue}</span>
            <span class="num" style="font-size: 18px; font-weight: 700; color: var(--text-muted);">in</span>
          </div>
          ${etFooter}
        </div>
        <div class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-5 rail-sky shadow-[var(--shadow)]">
          <div class="flex items-center justify-between">
            <p class="eyebrow">NEXT RAIN</p>
            <span class="num text-[9px] font-bold tracking-[0.12em] text-[var(--text-muted)]">FORECAST</span>
          </div>
          <div class="mt-4 flex items-baseline gap-2">
            <span class="num" style="font-size: 60px; font-weight: 800; line-height: 0.85; color: var(--text); letter-spacing: -0.03em;">${rainValue}</span>
            <span class="num" style="font-size: 18px; font-weight: 700; color: var(--text-muted);">in</span>
          </div>
          ${rainFooter}
        </div>
      </div>
    </section>
  `;
}

function heroRationale(run) {
  if (run.summary && run.summary.trim().length > 0) {
    return escapeHtml(run.summary);
  }
  if (Array.isArray(run.drivers) && run.drivers.length > 0) {
    return escapeHtml(run.drivers.slice(0, 2).join(". "));
  }
  return run.decision === "water"
    ? "Water deficit detected. Irrigate during the recommended window."
    : "Soil water is sufficient. Hold and monitor the next forecast cycle.";
}

export function RecommendationHero(run, { showRunButton = true } = {}) {
  if (!run) {
    return `
      <section class="hero-glow p-8">
        <div class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div class="max-w-3xl">
            <p class="eyebrow-muted">Current field status</p>
            <h2 class="mt-3 text-[38px] font-semibold tracking-[-0.05em] text-[var(--text)]">No recent irrigation recommendation</h2>
            <p class="mt-3 text-sm text-[var(--text-muted)]">Run an analysis to generate your first recommendation.</p>
          </div>
          <button
            type="button"
            data-nav="run-analysis"
            class="focus-outline inline-flex items-center gap-2 rounded-[6px] bg-[var(--ink)] px-5 py-3 text-xs font-extrabold tracking-[0.2em] text-[var(--amber)] shadow-[0_8px_22px_-8px_rgba(24,38,29,0.55)] transition-all duration-200 hover:brightness-110"
          >
            ${icon("sparkles", "h-4 w-4")}
            <span>RUN ANALYSIS →</span>
          </button>
        </div>
      </section>
    `;
  }

  const amount = (run.recommendedAmountIn ?? 0).toFixed(2);
  const timing = formatWindow(run.timingWindow).toUpperCase();
  const confidencePct = Math.round((run.confidenceScore ?? 0) * 100);
  const stressPct = Math.round((run.stressProbability ?? 0) * 100);
  const stressLabel = stressPct >= 60 ? "HIGH" : stressPct >= 30 ? "MODERATE" : "LOW";
  const soilTexture = run.inputSnapshot?.soilTexture ? escapeHtml(String(run.inputSnapshot.soilTexture).toUpperCase()) : "";
  const cropType = run.inputSnapshot?.cropType ? escapeHtml(String(run.inputSnapshot.cropType).toUpperCase()) : "";
  const growthStage = run.inputSnapshot?.growthStage ? escapeHtml(String(run.inputSnapshot.growthStage).replace(/_/g, " ").toUpperCase()) : "";
  const tempF = typeof run.inputSnapshot?.temperatureF === "number" ? Math.round(run.inputSnapshot.temperatureF) : null;
  const isHot = typeof tempF === "number" && tempF >= 90;

  return `
    <section class="hero-glow p-7 sm:p-8">
      <div class="grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)] xl:items-start">
        <div>
          <div class="flex items-center gap-3">
            ${decisionPill(run.decision)}
            <div class="dashed-rule"></div>
            <span class="num text-[13px] font-extrabold tracking-[0.14em] text-[var(--ink)]">${escapeHtml(timing)}</span>
          </div>

          <div class="mt-6 flex items-baseline gap-3">
            <span class="num" style="font-size: clamp(96px, 16vw, 148px); font-weight: 800; letter-spacing: -0.06em; line-height: 0.85; color: var(--ink);">${amount}</span>
            <div class="flex flex-col">
              <span class="text-[22px] font-bold tracking-[-0.02em] text-[var(--ink)]">inches</span>
              <span class="eyebrow-muted mt-1">${run.decision === "water" ? "OF WATER" : "HELD"}</span>
            </div>
          </div>

          <div class="mt-7 max-w-[440px] border-l-[3px] border-[var(--ink)] bg-[var(--panel-muted)] px-4 py-3">
            <p class="text-[14px] leading-6 text-[var(--text)]">${heroRationale(run)}</p>
          </div>
        </div>

        <div class="rounded-[12px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
          <div class="flex items-center gap-2">
            <span class="eyebrow">CONFIDENCE</span>
            <div class="h-px flex-1 bg-[var(--hairline)] opacity-40"></div>
          </div>
          <div class="mt-3 flex items-baseline gap-2">
            <span class="num" style="font-size: 56px; font-weight: 800; line-height: 0.85; color: var(--ink); letter-spacing: -0.03em;">${confidencePct}</span>
            <span class="num text-[20px] font-bold text-[var(--text-muted)]">%</span>
          </div>
          <div class="mt-3">
            ${confidenceBar(run.confidenceScore)}
          </div>
          <div class="mt-5 flex items-center justify-between border-t border-dashed border-[var(--hairline)] pt-4">
            <span class="text-[13px] font-semibold text-[var(--text-muted)]">Stress risk</span>
            <span class="num text-[12px] font-extrabold tracking-[0.14em] text-[var(--ink)]">${stressLabel}</span>
          </div>
        </div>
      </div>

      <div class="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-dashed border-[var(--hairline)] pt-5">
        <div class="flex flex-wrap gap-2">
          ${soilTexture ? `<span class="num rounded border border-[var(--border)] bg-[var(--panel-muted)] px-2.5 py-1 text-[10px] font-extrabold tracking-[0.14em] text-[var(--text)]">${soilTexture}</span>` : ""}
          ${cropType ? `<span class="num rounded border border-[var(--border)] bg-[var(--panel-muted)] px-2.5 py-1 text-[10px] font-extrabold tracking-[0.14em] text-[var(--text)]">${cropType}${growthStage ? ` · ${growthStage}` : ""}</span>` : ""}
          ${tempF != null ? `<span class="num rounded border ${isHot ? "border-[rgba(251,146,60,0.4)] bg-[rgba(251,146,60,0.12)] text-[var(--accent-warm)]" : "border-[var(--border)] bg-[var(--panel-muted)] text-[var(--text)]"} px-2.5 py-1 text-[10px] font-extrabold tracking-[0.14em]">${tempF}°F</span>` : ""}
        </div>
        ${showRunButton ? `
          <button
            type="button"
            data-nav="run-analysis"
            class="focus-outline inline-flex items-center gap-2 rounded-[6px] bg-[var(--ink)] px-5 py-3 text-xs font-extrabold tracking-[0.2em] text-[var(--amber)] shadow-[0_8px_22px_-8px_rgba(24,38,29,0.55)] transition-all duration-200 hover:brightness-110"
          >
            <span>RUN NEW ANALYSIS →</span>
          </button>
        ` : ""}
      </div>
    </section>
  `;
}

function DashboardHeroStatus() {
  return RecommendationHero(state.latestRun);
}

function RecentRunsSection() {
  const runs = state.runHistory.slice(0, 5);
  const body = runs.length > 0
    ? runs.map((run, index) => dashboardRunItem(run, index === runs.length - 1)).join("")
    : `<div class="px-4 py-6 text-center text-sm text-[var(--text-muted)]">No runs yet. Start with Run Analysis to populate the feed.</div>`;

  return `
    <section class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] shadow-[var(--shadow)]">
      <div class="flex items-center justify-between border-b border-dashed border-[var(--hairline)] px-4 py-3">
        <p class="eyebrow">RECENT RUNS</p>
        <button type="button" data-nav="history" class="focus-outline text-[11px] font-extrabold tracking-[0.12em] text-[var(--ink)] hover:underline">ALL RUNS →</button>
      </div>
      ${body}
    </section>
  `;
}

function QuickStartSection() {
  return `
    <section class="rounded-[12px] border border-[var(--border)] bg-[var(--panel)] p-4 shadow-[var(--shadow)]">
      <div class="flex items-center justify-between border-b border-dashed border-[var(--hairline)] pb-3">
        <p class="eyebrow">QUICK START</p>
        <span class="num text-[10px] font-bold tracking-[0.12em] text-[var(--text-muted)]">${Object.keys(PRESETS).length} SCENARIOS</span>
      </div>
      <div class="mt-3 grid gap-2">
        ${Object.entries(PRESETS)
          .map(
            ([key, preset]) => `
              <button
                type="button"
                data-preset="${key}"
                class="focus-outline flex w-full items-start justify-between gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-3 text-left transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--panel)]"
              >
                <div class="min-w-0">
                  <p class="text-sm font-bold text-[var(--text)]">${escapeHtml(preset.fieldName)}</p>
                  <p class="mt-0.5 truncate text-xs leading-5 text-[var(--text-muted)]">${escapeHtml(preset.analysisPrompt)}</p>
                </div>
                <span class="shrink-0 text-[var(--accent)]">${icon("sparkles", "h-4 w-4")}</span>
              </button>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

export function DashboardPage() {
  return `
    <section class="space-y-5">
      ${DashboardHeroStatus()}
      ${DashboardMetrics()}
      <div class="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
        ${RecentRunsSection()}
        ${QuickStartSection()}
      </div>
    </section>
  `;
}
