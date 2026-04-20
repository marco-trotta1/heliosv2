import { NAV_ITEMS, PAGE_TITLES, BRAND_LOGOS } from "../constants.js";
import { state } from "../state.js";
import { classNames, icon } from "./shared.js";

function BrandLogo() {
  const logoSrc = state.theme === "light" ? BRAND_LOGOS.light : BRAND_LOGOS.dark;
  return `
    <div class="flex h-20 items-center border-b border-[var(--border)] px-4 xl:px-5">
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
    <aside class="sticky top-0 flex h-screen flex-col border-r border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur">
      ${BrandLogo()}
      <nav class="flex-1 px-3 py-5 xl:px-4">
        <ul class="space-y-1">
          ${NAV_ITEMS.map(
            (item) => {
              const isActive = state.activePage === item.id;
              const isPrimary = item.id === "run-analysis";
              return `
              <li>
                <button
                  type="button"
                  data-nav="${item.id}"
                  class="${classNames(
                    "focus-outline group flex w-full items-center gap-3 rounded-[22px] px-3 py-3 text-left text-sm font-semibold transition-all duration-200",
                    isActive
                      ? isPrimary
                        ? "border border-[var(--accent)] bg-[var(--accent)] text-white shadow-[var(--shadow)]"
                        : "border border-[var(--border)] bg-[var(--panel)] text-[var(--text)] shadow-[var(--shadow)]"
                      : isPrimary
                        ? "border border-[var(--accent-soft)] bg-[var(--accent-soft)] text-[var(--accent)] hover:border-[var(--accent)] hover:bg-[var(--panel)]"
                        : "text-[var(--text-muted)] hover:bg-[var(--panel)] hover:text-[var(--text)]",
                  )}"
                >
                  <span class="${classNames(
                    "flex h-10 w-10 items-center justify-center rounded-[16px] border transition-colors duration-200",
                    isActive && isPrimary
                      ? "border-white/20 bg-white/12"
                      : "border-[var(--border)] bg-[var(--panel-muted)]",
                  )}">
                    ${icon(item.icon)}
                  </span>
                  <span class="hidden xl:block">${item.label}</span>
                </button>
              </li>
            `;
            },
          ).join("")}
        </ul>
      </nav>
      <div class="border-t border-[var(--border)] px-3 py-4 xl:px-4">
        <div class="flex items-center gap-3 rounded-[24px] border border-[var(--border)] bg-[var(--panel)] px-3 py-3 shadow-[var(--shadow)]">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            ${icon("user")}
          </div>
          <div class="hidden xl:block">
            <p class="text-sm font-semibold">Field Ops</p>
          </div>
        </div>
      </div>
    </aside>
  `;
}

export function TopBar() {
  return `
    <header class="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-[var(--border)] bg-[var(--bg)]/86 px-4 backdrop-blur sm:px-6">
      <div>
        <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">Helios</p>
        <h1 class="mt-1 text-[22px] font-semibold tracking-[-0.03em]">${PAGE_TITLES[state.activePage]}</h1>
      </div>
      <div class="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          id="theme-toggle"
          class="focus-outline inline-flex h-10 w-10 items-center justify-center rounded-[18px] border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--border-strong)] hover:text-[var(--text)]"
          aria-label="Toggle theme"
        >
          ${icon(state.theme === "dark" ? "sun" : "moon")}
        </button>
        <a
          href="https://github.com/marco-trotta1/heliosv2"
          target="_blank"
          rel="noopener noreferrer"
          class="focus-outline inline-flex h-10 w-10 items-center justify-center rounded-[18px] border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] shadow-[var(--shadow)] transition-all duration-200 hover:border-[var(--border-strong)] hover:text-[var(--text)]"
          aria-label="Open GitHub"
        >
          ${icon("github")}
        </a>
        <div class="flex h-10 w-10 items-center justify-center rounded-[18px] border border-[var(--border)] bg-[var(--panel)] text-[var(--text-muted)] shadow-[var(--shadow)]">
          ${icon("user")}
        </div>
      </div>
    </header>
  `;
}
