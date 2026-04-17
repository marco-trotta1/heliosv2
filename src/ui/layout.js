import { NAV_ITEMS, PAGE_TITLES, BRAND_LOGOS } from "../constants.js";
import { state } from "../state.js";
import { classNames, icon } from "./shared.js";

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
