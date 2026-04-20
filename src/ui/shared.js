import { state } from "../state.js";

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
    chevronDown:
      `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 9 6 6 6-6"/></svg>`,
  };
  return icons[name] || "";
}

export function copyText(value, trigger) {
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

export function PrimaryButton({ id = "", label, iconName = "", variant = "primary", extraClass = "", type = "button", disabled = false }) {
  const palette =
    variant === "primary"
      ? "border border-[var(--accent)] bg-[var(--accent)] text-white shadow-[var(--shadow)] hover:bg-[var(--accent-hover)] hover:border-[var(--accent-hover)]"
      : "border border-[var(--border)] bg-[var(--panel)] text-[var(--text)] hover:border-[var(--border-strong)] hover:bg-[var(--panel-hover)]";
  return `
    <button
      ${id ? `id="${id}"` : ""}
      type="${type}"
      ${disabled ? "disabled" : ""}
      class="${classNames(
        "focus-outline inline-flex items-center justify-center gap-2 rounded-[20px] px-4 py-2.5 text-sm font-semibold transition-all duration-200",
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

export function toggleControl(name, label, checked) {
  return `
    <label class="inline-flex items-center gap-3 rounded-[18px] border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-sm text-[var(--text)] shadow-[var(--shadow)]">
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

export function fieldCard(title, description, content, detail = "Tap to collapse") {
  return `
    <details open class="field-card surface-ring rounded-[26px] border border-[var(--border)] bg-[var(--panel)] p-5 shadow-[var(--shadow)]">
      <summary class="field-card-summary focus-outline flex cursor-pointer list-none items-start justify-between gap-4 rounded-[20px]">
        <div>
          <p class="text-[11px] font-bold uppercase tracking-[0.22em] text-[var(--accent)]">${title}</p>
          <h3 class="mt-2 text-lg font-semibold tracking-[-0.02em] text-[var(--text)]">${description}</h3>
        </div>
        <div class="field-card-meta inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel-muted)] px-3 py-1.5 text-xs font-medium text-[var(--text-muted)] transition-colors duration-200">
          <span>${detail}</span>
          <span class="field-card-chevron transition-transform duration-200">${icon("chevronDown", "h-4 w-4")}</span>
        </div>
      </summary>
      <div class="pt-5">
        ${content}
      </div>
    </details>
  `;
}

export function inputGroup(label, control, meta = "", helper = "") {
  return `
    <label class="block">
      <span class="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--text)]">
        <span>${label}</span>
        ${meta}
      </span>
      ${helper ? `<p class="mb-2 text-xs leading-5 text-[var(--text-muted)]">${helper}</p>` : ""}
      ${control}
    </label>
  `;
}

export function numericInput(name, value, min, step = "0.1", max = "") {
  return `
    <input
      name="${name}"
      type="number"
      value="${value}"
      min="${min}"
      ${max !== "" ? `max="${max}"` : ""}
      step="${step}"
      class="focus-outline w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-3 text-sm text-[var(--text)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:bg-[var(--panel)]"
    />
  `;
}

export function autoWeatherTag(name) {
  if (!state.weatherAutofill.autoFields[name]) {
    return "";
  }
  return `<span class="rounded-full border border-[var(--accent-cool-soft)] bg-[var(--accent-cool-soft)] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--accent-cool)]">Auto</span>`;
}

export function textInput(name, value) {
  return `
    <input
      name="${name}"
      type="text"
      value="${escapeHtml(value)}"
      class="focus-outline w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-3 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)] focus:bg-[var(--panel)]"
    />
  `;
}

export function selectInput(name, value, options) {
  return `
    <select
      name="${name}"
      class="focus-outline w-full rounded-[18px] border border-[var(--border)] bg-[var(--panel-muted)] px-3.5 py-3 text-sm text-[var(--text)] outline-none transition-all duration-200 focus:border-[var(--accent)] focus:bg-[var(--panel)]"
    >
      ${options
        .map((option) => `<option value="${option.value}" ${value === option.value ? "selected" : ""}>${option.label}</option>`)
        .join("")}
    </select>
  `;
}

export function checkboxGroup(title, name, options, selected) {
  return `
    <fieldset class="rounded-[24px] border border-[var(--border)] bg-[var(--panel-muted)] p-4">
      <legend class="px-1 text-sm font-semibold text-[var(--text)]">${title}</legend>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        ${options
          .map(
            (option) => `
              <label class="inline-flex items-center gap-3 rounded-[18px] border border-[var(--border)] bg-[var(--panel)] px-3 py-2.5 text-sm text-[var(--text)] shadow-[var(--shadow)]">
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

export function emptyBlock(title, body) {
  return `
    <div class="rounded-[28px] border border-dashed border-[var(--border)] bg-[var(--panel-muted)] px-5 py-10 text-center">
      <p class="text-sm font-semibold text-[var(--text)]">${title}</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">${body}</p>
    </div>
  `;
}

export function emptyInspectorState() {
  return `
    <div class="rounded-[28px] border border-dashed border-[var(--border)] bg-[var(--panel)] px-6 py-12 text-center shadow-[var(--shadow)]">
      <p class="text-sm font-semibold text-[var(--text)]">No analysis yet. Run a prompt to generate results.</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">Recent field decisions will appear here for review, copying, and reuse.</p>
    </div>
  `;
}
