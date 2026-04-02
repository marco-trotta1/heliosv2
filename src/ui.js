import { NAV_ITEMS, PAGE_TITLES, PRESETS, BRAND_LOGOS } from "./constants.js";
import {
  round,
  formatPercent,
  formatWindow,
  formatTimestamp,
  recommendationTone,
  serializeRunForCopy,
} from "./domain.js";
import {
  state,
  runtimeConfig,
  isLiveApiMode,
  setPage,
  toggleTheme,
  applyPreset,
  saveLatestRun,
  updateFormField,
  updateArrayField,
} from "./state.js";
import { evaluateScenario, submitFeedback } from "./api.js";
import { validateForm } from "./validation.js";

// ── Utility ────────────────────────────────────────────────────────────────────

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

export function icon(name, className = "h-5 w-5") {
  const icons = {
    layout:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>`,
    sparkles:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z"/><path d="M19 14l.9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14z"/><path d="M5 14l.7 1.6L7.3 16l-1.6.7L5 18.3l-.7-1.6L2.7 16l1.6-.4L5 14z"/></svg>`,
    history:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 7v5l3 2"/></svg>`,
    bookmark:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4h12a1 1 0 0 1 1 1v15l-7-4-7 4V5a1 1 0 0 1 1-1z"/></svg>`,
    settings:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.06.06a2 2 0 1 1-2.82 2.82l-.06-.06a1.8 1.8 0 0 0-1.98-.36 1.8 1.8 0 0 0-1.1 1.64V21a2 2 0 1 1-4 0v-.09a1.8 1.8 0 0 0-1.1-1.64 1.8 1.8 0 0 0-1.98.36l-.06.06a2 2 0 1 1-2.82-2.82l.06-.06A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.64-1.1H2.9a2 2 0 1 1 0-4h.09a1.8 1.8 0 0 0 1.64-1.1 1.8 1.8 0 0 0-.36-1.98l-.06-.06A2 2 0 1 1 7.03 4l.06.06a1.8 1.8 0 0 0 1.98.36h.01A1.8 1.8 0 0 0 10.18 2.8V2.7a2 2 0 1 1 4 0v.09a1.8 1.8 0 0 0 1.1 1.64 1.8 1.8 0 0 0 1.98-.36l.06-.06A2 2 0 1 1 20.14 7l-.06.06a1.8 1.8 0 0 0-.36 1.98v.01a1.8 1.8 0 0 0 1.64 1.1h.09a2 2 0 1 1 0 4h-.09a1.8 1.8 0 0 0-1.64 1.1z"/></svg>`,
    github:
      `<svg class="${className}" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.65.5.5 5.65.5 12A11.5 11.5 0 0 0 8.36 22.94c.58.11.79-.25.79-.56v-2.02c-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.71.08-.71 1.17.08 1.78 1.2 1.78 1.2 1.03 1.78 2.71 1.27 3.37.97.1-.75.4-1.27.73-1.57-2.55-.29-5.23-1.27-5.23-5.67 0-1.25.45-2.27 1.19-3.07-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.18 1.18a10.92 10.92 0 0 1 5.8 0c2.21-1.5 3.18-1.18 3.18-1.18.63 1.58.23 2.75.11 3.04.74.8 1.19 1.82 1.19 3.07 0 4.41-2.69 5.37-5.25 5.66.41.36.77 1.06.77 2.14v3.18c0 .31.21.68.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg>`,
    sun:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M4.93 4.93l1.77 1.77M17.3 17.3l1.77 1.77M2 12h2.5M19.5 12H22M4.93 19.07l1.77-1.77M17.3 6.7l1.77-1.77"/></svg>`,
    moon:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.79A9 9 0 0 1 11.21 3a7 7 0 1 0 9.79 9.79z"/></svg>`,
    copy:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    check:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m5 13 4 4L19 7"/></svg>`,
    user:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/></svg>`,
    chart:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5-6"/></svg>`,
    chevronDown:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 9 6 6 6-6"/></svg>`,
  };
  return icons[name] || "";
}

// ── Clipboard helper ───────────────────────────────────────────────────────────

function copyText(value, trigger) {
  const onCopySuccess = () => {
    if (!trigger) {
      return;
    }
    trigger.innerHTML = `${icon("check", "h-4 w-4")} <span>Copied</span>`;
    window.setTimeout(() => {
      trigger.innerHTML = `${icon("copy", "h-4 w-4")} <span>Copy</span>`;
    }, 1200);
  };

  const onCopyFailure = () => {
    if (!trigger) {
      return;
    }
    trigger.innerHTML = `${icon("copy", "h-4 w-4")} <span>Copy failed</span>`;
  };

  const fallbackCopy = () => {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    textarea.style.pointerEvents = "none";
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    document.body.removeChild(textarea);
    if (copied) {
      onCopySuccess();
      return;
    }
    onCopyFailure();
  };

  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(value).then(onCopySuccess).catch(fallbackCopy);
    return;
  }
  fallbackCopy();
}

// ── Form helpers ───────────────────────────────────────────────────────────────

function parseNumberInput(value, fallback) {
  if (value === "") {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function parseFieldValue(target, fallback) {
  if (target.type === "number") {
    return parseNumberInput(target.value, fallback);
  }
  return target.value;
}

function syncFormState(form) {
  const formData = new FormData(form);
  for (const [key, value] of formData.entries()) {
    if (key === "waterWindow" || key === "energyWindow") {
      continue;
    }
    const field = form.elements.namedItem(key);
    if (field instanceof HTMLInputElement && field.type === "checkbox") {
      state.form[key] = field.checked;
    } else if (field instanceof HTMLInputElement && field.type === "number") {
      state.form[key] = parseNumberInput(value, state.form[key]);
    } else {
      state.form[key] = value;
    }
  }
  state.form.waterWindow = [...form.querySelectorAll('input[name="waterWindow"]:checked')].map((item) => item.value);
  state.form.energyWindow = [...form.querySelectorAll('input[name="energyWindow"]:checked')].map((item) => item.value);
}

function autoSizeTextarea(textarea) {
  textarea.style.height = "0px";
  textarea.style.height = `${textarea.scrollHeight}px`;
}

function resizePromptInput() {
  const prompt = document.querySelector("#analysis-prompt");
  if (prompt) {
    autoSizeTextarea(prompt);
  }
}

// ── Feedback summary ───────────────────────────────────────────────────────────

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

// ── Component helpers ──────────────────────────────────────────────────────────

function PrimaryButton({ id = "", label, iconName = "", variant = "primary", extraClass = "", type = "button", disabled = false }) {
  const palette =
    variant === "primary"
      ? "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"
      : "border border-[var(--border)] bg-[var(--panel-muted)] text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)]";
  return `
    <button
      ${id ? `id="${id}"` : ""}
      type="${type}"
      ${disabled ? "disabled" : ""}
      class="${classNames(
        "inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-200",
        disabled ? "cursor-not-allowed opacity-60" : "",
        palette,
        extraClass,
      )}"
    >
      ${iconName ? icon(iconName, "h-4 w-4") : ""}
      <span>${label}</span>
    </button>
  `;
}

function toggleControl(name, label, checked) {
  return `
    <label class="inline-flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm text-[var(--text)]">
      <input
        type="checkbox"
        name="${name}"
        ${checked ? "checked" : ""}
        class="h-4 w-4 rounded border-[var(--border)] bg-transparent text-[var(--accent)] focus:ring-[var(--accent)]"
      />
      <span>${label}</span>
    </label>
  `;
}

function fieldCard(title, description, content) {
  return `
    <section class="rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] p-5">
      <div class="mb-5">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">${title}</p>
        <h3 class="mt-2 text-base font-medium text-[var(--text)]">${description}</h3>
      </div>
      ${content}
    </section>
  `;
}

function inputGroup(label, control) {
  return `
    <label class="block">
      <span class="mb-2 block text-sm font-medium text-[var(--text-muted)]">${label}</span>
      ${control}
    </label>
  `;
}

function numericInput(name, value, min, step = "0.1", max = "") {
  return `
    <input
      name="${name}"
      type="number"
      value="${value}"
      min="${min}"
      ${max !== "" ? `max="${max}"` : ""}
      step="${step}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    />
  `;
}

function textInput(name, value) {
  return `
    <input
      name="${name}"
      type="text"
      value="${escapeHtml(value)}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    />
  `;
}

function selectInput(name, value, options) {
  return `
    <select
      name="${name}"
      class="w-full rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
    >
      ${options
        .map((option) => `<option value="${option.value}" ${value === option.value ? "selected" : ""}>${option.label}</option>`)
        .join("")}
    </select>
  `;
}

function checkboxGroup(title, name, options, selected) {
  return `
    <fieldset class="rounded-3xl border border-[var(--border)] bg-[var(--panel-muted)] p-4">
      <legend class="px-1 text-sm font-medium text-[var(--text-muted)]">${title}</legend>
      <div class="mt-3 grid gap-3">
        ${options
          .map(
            (option) => `
              <label class="inline-flex items-center gap-3 text-sm text-[var(--text)]">
                <input
                  type="checkbox"
                  name="${name}"
                  value="${option.value}"
                  ${selected.includes(option.value) ? "checked" : ""}
                  class="h-4 w-4 rounded border-[var(--border)] bg-transparent text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <span>${option.label}</span>
              </label>
            `,
          )
          .join("")}
      </div>
    </fieldset>
  `;
}

function emptyBlock(title, body) {
  return `
    <div class="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--panel-muted)] px-5 py-10 text-center">
      <p class="text-sm font-medium text-[var(--text)]">${title}</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">${body}</p>
    </div>
  `;
}

function emptyInspectorState() {
  return `
    <div class="rounded-[28px] border border-dashed border-[var(--border)] bg-[var(--panel)] px-6 py-12 text-center">
      <p class="text-sm font-medium text-[var(--text)]">No analysis yet. Run a prompt to generate results.</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">Results will appear here as reusable cards with copy actions and timestamps.</p>
    </div>
  `;
}

// ── Layout components ──────────────────────────────────────────────────────────

function BrandLogo() {
  const logoSrc = state.theme === "light" ? BRAND_LOGOS.light : BRAND_LOGOS.dark;
  return `
    <div class="flex h-16 items-center border-b border-[var(--border)] px-4">
      <div class="h-10 w-10 overflow-hidden xl:h-9 xl:w-[198px]">
        <img
          src="${logoSrc}"
          alt="Irrigant"
          width="440"
          height="80"
          class="block h-10 w-auto max-w-none xl:h-9"
          decoding="async"
          draggable="false"
        />
      </div>
    </div>
  `;
}

export function Sidebar() {
  return `
    <aside class="sticky top-0 flex h-screen flex-col border-r border-[var(--border)] bg-[var(--bg)]">
      ${BrandLogo()}
      <nav class="flex-1 px-3 py-5">
        <ul class="space-y-1">
          ${NAV_ITEMS.map(
            (item) => `
              <li>
                <button
                  type="button"
                  data-nav="${item.id}"
                  class="${classNames(
                    "group flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium transition-all duration-200",
                    state.activePage === item.id
                      ? "bg-[var(--accent-soft)] text-[var(--text)]"
                      : "text-[var(--text-muted)] hover:bg-[var(--panel-hover)] hover:text-[var(--text)]",
                  )}"
                >
                  <span class="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--panel)]">
                    ${icon(item.icon)}
                  </span>
                  <span class="hidden xl:block">${item.label}</span>
                </button>
              </li>
            `,
          ).join("")}
        </ul>
      </nav>
      <div class="border-t border-[var(--border)] px-3 py-4">
        <div class="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--panel)] px-3 py-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            ${icon("user")}
          </div>
          <div class="hidden xl:block">
            <p class="text-sm font-medium">Field Ops</p>
            <p class="text-xs text-[var(--text-muted)]">Prototype tenant</p>
          </div>
        </div>
      </div>
    </aside>
  `;
}

export function TopBar() {
  return `
    <header class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--border)] bg-[var(--bg)] px-4 backdrop-blur sm:px-6">
      <div>
        <h1 class="text-[22px] font-semibold tracking-tight">${PAGE_TITLES[state.activePage]}</h1>
      </div>
      <div class="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          id="theme-toggle"
          class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
          aria-label="Toggle theme"
        >
          ${icon(state.theme === "dark" ? "sun" : "moon")}
        </button>
        <a
          href="https://github.com/marco-trotta1/heliosv2"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--accent)] hover:text-[var(--text)]"
          aria-label="Open GitHub"
        >
          ${icon("github")}
        </a>
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)]">
          ${icon("user")}
        </div>
      </div>
    </header>
  `;
}

// ── Page components ────────────────────────────────────────────────────────────

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
            <span class="rounded-full bg-[var(--panel)] px-3 py-1 text-xs font-medium text-[var(--text-muted)]">${run.recommendedAmountIn.toFixed(2)} in</span>
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
          <h2 class="mt-4 text-3xl font-semibold tracking-tight text-[var(--text)]">${run.decision === "water" ? `Apply ${run.recommendedAmountIn.toFixed(2)} in ${escapeHtml(formatWindow(run.timingWindow)).toLowerCase()}` : "Hold irrigation for now"}</h2>
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
            <span class="text-3xl font-semibold tracking-tight ${tone.amount}">${run.recommendedAmountIn.toFixed(2)}</span>
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

function FieldProfileSection() {
  return fieldCard(
    "Field Profile",
    "Crop, soil, and terrain descriptors",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Field name", textInput("fieldName", state.form.fieldName))}
      ${inputGroup("Farm ID", textInput("farmId", state.form.farmId))}
      ${inputGroup("Field area (ac)", numericInput("fieldAreaAcres", state.form.fieldAreaAcres, "1"))}
      ${inputGroup("Latitude", numericInput("locationLat", state.form.locationLat, "-90", "0.0001", "90"))}
      ${inputGroup("Longitude", numericInput("locationLon", state.form.locationLon, "-180", "0.0001", "180"))}
      ${inputGroup("Crop type", selectInput("cropType", state.form.cropType, [
        { value: "corn", label: "Corn" },
        { value: "soybean", label: "Soybean" },
        { value: "potato", label: "Potato" },
        { value: "alfalfa", label: "Alfalfa" },
        { value: "wheat", label: "Wheat" },
      ]))}
      ${inputGroup("Growth stage", selectInput("growthStage", state.form.growthStage, [
        { value: "emergence", label: "Emergence" },
        { value: "vegetative", label: "Vegetative" },
        { value: "flowering", label: "Flowering" },
        { value: "grain_fill", label: "Grain fill" },
        { value: "maturity", label: "Maturity" },
      ]))}
      ${inputGroup("Soil texture", selectInput("soilTexture", state.form.soilTexture, [
        { value: "sand", label: "Sand" },
        { value: "loam", label: "Loam" },
        { value: "clay", label: "Clay" },
      ]))}
      ${inputGroup("Drainage", selectInput("drainageClass", state.form.drainageClass, [
        { value: "poor", label: "Poor" },
        { value: "moderate", label: "Moderate" },
        { value: "well", label: "Well drained" },
      ]))}
      ${inputGroup("Infiltration rate (in/hr)", numericInput("infiltrationRate", state.form.infiltrationRate, "0.01"))}
      ${inputGroup("Slope (%)", numericInput("slopePct", state.form.slopePct, "0"))}
    </div>`,
  );
}

function SensorFeedSection() {
  return fieldCard(
    "Sensor Feed",
    "Soil moisture and weather inputs",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Current soil moisture", numericInput("currentMoisture", state.form.currentMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("6h ago moisture", numericInput("lagOneMoisture", state.form.lagOneMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("12h ago moisture", numericInput("lagTwoMoisture", state.form.lagTwoMoisture, "0.05", "0.01", "0.6"))}
      ${inputGroup("Temperature (°F)", numericInput("temperatureF", state.form.temperatureF, "-58"))}
      ${inputGroup("Humidity (%)", numericInput("humidityPct", state.form.humidityPct, "0", "1", "100"))}
      ${inputGroup("Wind (mph)", numericInput("windMph", state.form.windMph, "0"))}
      ${inputGroup("Forecast precipitation (in)", numericInput("precipitationIn", state.form.precipitationIn, "0"))}
      ${inputGroup("Solar radiation (MJ/m²)", numericInput("solarRadiationMjM2", state.form.solarRadiationMjM2, "0"))}
    </div>`,
  );
}

function OperationsSection() {
  return fieldCard(
    "Operations",
    "System constraints and scheduling rules",
    `<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
      ${inputGroup("Irrigation type", selectInput("irrigationType", state.form.irrigationType, [
        { value: "pivot", label: "Pivot" },
        { value: "drip", label: "Drip" },
        { value: "flood", label: "Flood" },
      ]))}
      ${inputGroup("Pump capacity (in/hr)", numericInput("pumpCapacity", state.form.pumpCapacity, "0.01"))}
      ${inputGroup("Max irrigation volume (in)", numericInput("maxIrrigationVolume", state.form.maxIrrigationVolume, "0"))}
      ${inputGroup("Budget ($)", numericInput("budgetDollars", state.form.budgetDollars, "0", "1"))}
      ${inputGroup("Irrigation last 24h (in)", numericInput("recentIrrigation24h", state.form.recentIrrigation24h, "0"))}
      ${inputGroup("Irrigation last 72h (in)", numericInput("recentIrrigation72h", state.form.recentIrrigation72h, "0"))}
    </div>
    <div class="mt-5 grid gap-4">
      ${checkboxGroup("Water rights schedule", "waterWindow", [
        { value: "tonight", label: "Tonight" },
        { value: "tomorrow_morning", label: "Tomorrow morning" },
        { value: "tomorrow_afternoon", label: "Tomorrow afternoon" },
        { value: "tomorrow_night", label: "Tomorrow night" },
      ], state.form.waterWindow)}
      ${checkboxGroup("Lower-cost energy windows", "energyWindow", [
        { value: "tonight", label: "Tonight" },
        { value: "tomorrow_morning", label: "Tomorrow morning" },
        { value: "tomorrow_afternoon", label: "Tomorrow afternoon" },
        { value: "tomorrow_night", label: "Tomorrow night" },
      ], state.form.energyWindow)}
    </div>`,
  );
}

function DataSection() {
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="max-w-3xl">
        <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Data</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-[var(--text)]">Supporting field context</h2>
        <p class="mt-3 text-sm leading-7 text-[var(--text-muted)]">
          Review or update the field details that support the recommendation. These inputs stay grouped together so they inform the decision without competing with it.
        </p>
      </div>
      <div class="mt-6 grid gap-4 xl:grid-cols-3">
        ${FieldProfileSection()}
        ${SensorFeedSection()}
        ${OperationsSection()}
      </div>
    </section>
  `;
}

function PromptInput() {
  const modeLabel =
    state.analysis.source === "api"
      ? "Live API mode"
      : state.analysis.source === "local"
        ? "Fallback mode"
        : "Demo mode";
  return `
    <section class="rounded-[28px] border border-[var(--border)] bg-[var(--panel)] p-6 shadow-[var(--shadow)]">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-sm font-medium uppercase tracking-[0.18em] text-[var(--text-muted)]">Prompt</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-[var(--text)]">Describe the field situation and what you need to decide</h2>
          <p class="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-muted)]">
            Start here. Enter the request in plain language, then review the recommendation below before checking supporting data.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <div class="hidden rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-xs text-[var(--text-muted)] sm:block">
            ${modeLabel}
          </div>
          ${Object.keys(PRESETS)
            .map((key) => PrimaryButton({ label: key === "heatwave" ? "Heat wave" : key === "balanced" ? "Balanced day" : "Rain incoming", iconName: "sparkles", variant: "secondary", extraClass: "preset-trigger", id: "", type: "button" }).replace("<button", `<button data-preset="${key}"`))
            .join("")}
        </div>
      </div>
      <textarea
        id="analysis-prompt"
        name="analysisPrompt"
        rows="4"
        class="mt-5 w-full rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-4 text-sm leading-7 text-[var(--text)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] focus:border-[var(--accent)]"
        placeholder="Enter your request, scenario, or irrigation question here..."
      >${escapeHtml(state.form.analysisPrompt)}</textarea>
      <div class="mt-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div class="flex flex-1 flex-col gap-4">
          <div class="rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-4 py-3 text-sm text-[var(--text-muted)]">
            <p>${escapeHtml(state.analysis.status)}</p>
            ${state.analysis.error ? `<p class="mt-2 text-[var(--accent-warm)]">${escapeHtml(state.analysis.error)}</p>` : ""}
            <p class="mt-2">Prototype note: synthetic training data, approximate ET, heuristic confidence, and rule-based optimization.</p>
          </div>
          <div class="flex flex-1 flex-col gap-3 xl:flex-row xl:items-center">
          <label class="text-sm text-[var(--text-muted)]">
            <span class="mb-2 block text-sm font-medium text-[var(--text-muted)]">Model</span>
            <select
              name="model"
              class="min-w-[180px] rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2.5 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)]"
            >
              ${["Helios Core", "Helios Balanced", "Helios Conservative"]
                .map((option) => `<option value="${option}" ${state.form.model === option ? "selected" : ""}>${option}</option>`)
                .join("")}
            </select>
          </label>
          <div class="flex flex-wrap items-center gap-3 pt-1">
            ${toggleControl("autoSave", "Auto-save run", state.form.autoSave)}
            ${toggleControl("includeNotes", "Detailed notes", state.form.includeNotes)}
          </div>
        </div>
        </div>
        <div class="flex justify-start xl:justify-end">
          ${PrimaryButton({
          id: "run-analysis-button",
          label: state.analysis.submitting ? "Running..." : "Run analysis",
          iconName: "sparkles",
          variant: "primary",
          type: "submit",
          extraClass: "min-w-[160px]",
          disabled: state.analysis.submitting,
        })}
        </div>
      </div>
    </section>
  `;
}

export function RecommendationSpotlight() {
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
            <span class="text-5xl font-semibold tracking-tight ${tone.amount}">${run.recommendedAmountIn.toFixed(2)}</span>
            <span class="pb-1 text-lg font-medium text-[var(--text-muted)]">in</span>
          </div>
          <p class="mt-4 text-sm text-[var(--text-muted)]">This is the number the operator should notice first.</p>
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
            ${isLiveApiMode() ? "" : "disabled"}
            class="${classNames(
              "inline-flex items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-2 text-sm font-medium text-[var(--text)] transition-all duration-200",
              isLiveApiMode() ? "hover:border-[var(--accent)]" : "cursor-not-allowed opacity-60",
            )}"
          >
            ${isLiveApiMode() ? "Submit Feedback" : "Live API required"}
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
  `;
}

function AnalysisConsoleDisclosure() {
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

export function AnalysisWorkspace() {
  return `
    <section class="space-y-6">
      <form id="analysis-form" class="space-y-6">
        ${PromptInput()}
        ${RecommendationSpotlight()}
        ${DataSection()}
        ${AnalysisConsoleDisclosure()}
      </form>
    </section>
  `;
}

// ── Root render ────────────────────────────────────────────────────────────────

const app = document.querySelector("#app");

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
  resizePromptInput();
}

// ── Event binding ──────────────────────────────────────────────────────────────

export function bindAppEvents() {
  document.querySelectorAll("[data-nav]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.nav));
  });

  document.querySelector("#theme-toggle")?.addEventListener("click", toggleTheme);
  document.querySelector("#theme-toggle-inline")?.addEventListener("click", toggleTheme);

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => applyPreset(button.dataset.preset));
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => {
      const run = [...state.runHistory, ...state.savedRuns].find((item) => item.id === button.dataset.copy);
      if (run) {
        copyText(run.copyText, button);
      }
    });
  });

  const form = document.querySelector("#analysis-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      syncFormState(form);
      const validationError = validateForm(state.form);
      if (validationError) {
        state.analysis.error = validationError;
        state.analysis.status = "Please fix the input errors before running.";
        renderApp();
        return;
      }
      evaluateScenario();
    });

    form.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      if (target instanceof HTMLInputElement && target.type === "checkbox") {
        if (target.name === "waterWindow" || target.name === "energyWindow") {
          updateArrayField(target.name, target.value, target.checked);
        } else {
          updateFormField(target.name, target.checked);
        }
      } else if (target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement) {
        updateFormField(target.name, parseFieldValue(target, state.form[target.name]));
      }

      if (target instanceof HTMLTextAreaElement) {
        autoSizeTextarea(target);
      }
    });
  }

  document.querySelector("#save-latest-run")?.addEventListener("click", saveLatestRun);
  document.querySelector("#analysis-console-toggle")?.addEventListener("click", () => {
    state.analysisConsoleOpen = !state.analysisConsoleOpen;
    renderApp();
  });
  document.querySelector("#feedback-toggle")?.addEventListener("click", () => {
    state.feedbackForm.open = !state.feedbackForm.open;
    state.feedbackForm.error = "";
    renderApp();
  });
  document.querySelector("#feedback-submit")?.addEventListener("click", submitFeedback);
  document.querySelector('select[name="feedbackOutcome"]')?.addEventListener("input", (event) => {
    state.feedbackForm.outcome = event.target.value;
  });
  document.querySelector('input[name="feedbackYieldDelta"]')?.addEventListener("input", (event) => {
    state.feedbackForm.yieldDelta = event.target.value;
  });
  document.querySelector("#feedback-notes")?.addEventListener("input", (event) => {
    state.feedbackForm.notes = event.target.value;
    autoSizeTextarea(event.target);
  });
}
