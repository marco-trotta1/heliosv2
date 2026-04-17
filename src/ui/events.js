import { evaluateScenario, logAcknowledgement, submitFeedback } from "../api.js";
import { state, applyPreset, saveLatestRun, setPage, toggleTheme, storeRun } from "../state.js";
import { validateForm } from "../validation.js";
import { copyText } from "./shared.js";
import { autoSizeTextarea, resizePromptInput, syncFormState, updateFormStateFromInput } from "./form-state.js";

export function bindAppEvents({ renderApp, scheduleWeatherAutofill }) {
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
      const formErrorEl = document.querySelector("#form-error");
      if (validationError) {
        if (formErrorEl) {
          formErrorEl.textContent = validationError;
          formErrorEl.style.display = "block";
        }
        return;
      }
      if (formErrorEl) {
        formErrorEl.textContent = "";
        formErrorEl.style.display = "none";
      }
      evaluateScenario();
    });

    form.addEventListener("input", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      updateFormStateFromInput(target, form, (delayMs) => scheduleWeatherAutofill(renderApp, delayMs));

      if (target instanceof HTMLTextAreaElement) {
        autoSizeTextarea(target);
      }
    });
  }

  document.querySelector("#acknowledge-proceed-btn")?.addEventListener("click", async () => {
    const run = state.acknowledgement.pendingRun;
    if (!run) {
      return;
    }
    await logAcknowledgement(run);
    storeRun(run);
    state.acknowledgement.pendingRun = null;
    renderApp();
  });

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

  resizePromptInput();
}
