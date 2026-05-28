# Helios UI Redesign — Design Spec

**Date:** 2026-05-27
**Status:** Draft — awaiting user review
**Author:** Marco + Claude (brainstorming session)

## Goal

Make the Helios UI sleeker. A farmer must be able to understand the decision in
five seconds; a YC partner must read the surface as enterprise-credible. The
current UI is visually distinctive but busy — paper-wash gradients, multi-color
metric cards, oversized inches headline, decorative dashed rules, multiple
eyebrow labels, dual hero on dashboard + run-analysis. We strip ornament, keep
the agricultural soul (forest-green accent, deep-ink text), and reorganize the
dashboard around the **decision**, not the metric.

## Audience and use

Primary user: **farmer** — likely on a phone, in a truck or field, one-handed,
needs the irrigation answer immediately.

Secondary user: **irrigation district manager** — desktop, evaluating
recommendations across fields, reviewing run history.

The visual register must satisfy both: farmer-clear copy + enterprise-credible
polish.

## Approach

**B — Decision-First Reorganization.** Restructure the dashboard around a hero
card that *speaks* in plain English ("Hold. Your soil is wet enough through
Tuesday."). Demote supporting numbers to a clean hairline-separated evidence
strip. Move Recent Runs and demo-mode scenarios to secondary zones. Reuse the
same hero + evidence-strip components on the Results screen.

Implementation stays on vanilla JS in the existing `src/ui/` modules. No
framework migration. No backend changes.

## Design system

### Color tokens — light (default)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#f8f7f4` | App background — warm-neutral off-white (not cream) |
| `--panel` | `#ffffff` | Card / surface |
| `--panel-muted` | `#f0eee8` | Secondary surface, hover |
| `--ink` | `#18261d` | Primary text |
| `--ink-muted` | `#5b6c63` | Secondary text, labels |
| `--accent` | `#244f3c` | Single brand accent — forest green |
| `--hairline` | `rgba(24,38,29,0.10)` | Borders |
| `--warn` | `#9f6637` | "Apply" state (terracotta) |
| `--ok` | `#2e6e52` | "Hold" / nominal |

### Color tokens — dark

| Token | Value |
|---|---|
| `--bg` | `#0f1410` |
| `--panel` | `#161e19` |
| `--panel-muted` | `#1c2620` |
| `--ink` | `#e8ede5` |
| `--ink-muted` | `#9aa89e` |
| `--accent` | `#81b18d` |
| `--hairline` | `rgba(232,237,229,0.10)` |
| `--warn` | `#d89b61` |
| `--ok` | `#80c19a` |

### Typography

- Single family: **Inter** (already loaded). Geist removed.
- Numeric data uses Inter's tabular-nums feature (`font-variant-numeric: tabular-nums`). No separate mono family.
- Scale: 12 / 14 / 16 / 20 / 28 / 44 px.
- Weights: 400 / 500 / 600 / 700.
- Decision word ("Hold." / "Apply."): 44px, weight 600.
- Decision sentence: 20px, weight 400, line-height 1.4.
- Labels: 11px, weight 600, letter-spacing 0.08em, uppercase, ink-muted. (Toned from the 0.22–0.24em letter-spacing of the current eyebrows.)

### Spacing and shape

- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 px.
- Radius: 8 (cards), 6 (buttons / pills), 999 (full-round indicators only).
- Shadow: `--shadow` (`0 1px 2px rgba(24,38,29,0.04), 0 8px 24px -16px rgba(24,38,29,0.12)`) and `--shadow-strong` for the hero card. No glow effects, no hero-glow pseudo-elements.

### CSS deletions

From `styles.css`: `.hero-glow` and pseudo-elements, `--paper-wash`,
`--glow-warm`, `--glow-cool`, all four `--metric-*-bg` gradients, the
`--rail-warm/forest/sky` colored top borders, `.spotlight-water`,
`.spotlight-wait`, `.accent-divider`, `.surface-ring`, the dashed-rule
decoration when used mid-content. ~200 lines of CSS removed. Net target file
size: ~350 lines.

## Layout and navigation

### Desktop (≥ 1024px)

- Left sidebar, 240px fixed. Top: brand wordmark (14px, weight 600). Middle:
  4 text-only nav items with a 2px accent left-rule on the active item. Bottom:
  theme toggle + a 24px chip showing demo/live mode.
- Main column, max-width 960px, centered, 32px horizontal padding.
- No separate topbar. Page CTAs live in the main column.
- No GitHub link in chrome.
- The current sticky cream demo-mode banner is replaced by the sidebar-footer
  chip.

### Tablet (640–1023px)

- Sidebar collapses to a 56px icon rail (text labels appear on hover).

### Mobile (< 640px)

- No sidebar. Top: 48px fixed bar with brand wordmark left, demo chip right.
- Bottom tab bar with **two destinations**: Dashboard, Run. History/Saved/Settings live behind a "More" sheet.

### Navigation items

Four: **Dashboard · Run Analysis · Runs · Settings.**

- History and Saved Runs merge into **Runs** with filter pills (`All` / `Saved` / `Last 7 days` / `Apply only` / `Hold only`).
- The current "Field Ops" sidebar item is removed (assumed to be dead prototype scaffolding; reinstate if it has a destination).

## Dashboard composition

Three zones, top to bottom.

### Zone 1 — Decision hero

Single card, full-width within the 960px column, ~280px tall. Contents:

- **Decision word** ("Hold." / "Apply.") — 44px, weight 600, plain period, ink color. When the decision is *Apply*, the word picks up `--warn`; when *Hold*, `--ok`.
- **Decision sentence** — 20px, weight 400, line-height 1.4. Plain English explaining *why*. Examples:
  - "Your soil is wet enough through Tuesday."
  - "0.6 inches today — soil is dry and no rain coming through Friday."
  - "Check the moisture probe before deciding; readings are stale."
- **Confidence** — single line, 14px ink-muted: `High confidence · 79%`. No bar, no dot, no stress-risk chip.
- **Action** — one secondary button, top-right inside card: `Run new analysis`.

No `See why ▾` button. The evidence strip below is the why.

### Zone 2 — Evidence strip

Hairline-separated row of 4 metrics: **Soil Moisture · ET (24h) · Rain (24h) · Next Rain**. No cards, no gradient backgrounds, no top-rail colors.

- Label: 11px, weight 600, letter-spacing 0.08em, uppercase, ink-muted.
- Value: 20px, weight 500, tabular nums, ink.
- Click any metric → details popover (source, last updated, raw value).
- Mobile: 2×2 grid.

### Zone 3 — Recent Runs + Try a Scenario

Two subsections, side-by-side on desktop, stacked on mobile.

- **Recent Runs:** vertical list of the last 5 runs. Columns: field · date · decision · inches. (Runtime and conf% are removed — runtime is irrelevant to a farmer, conf is already in the hero.) No table chrome. Footer link: `View all runs →`.
- **Try a Scenario:** plain text links with one-line descriptions. **Demo-mode only** (`HELIOS_CONFIG.mode === 'demo'`). Hidden in live mode.

Section headers: 12px uppercase ink-muted label + dashed hairline beneath. Dashed-rule decoration is retained *only* as a typographic section header device; removed from mid-content use.

### Redundancy deletions from the current dashboard

- The HOLD/APPLY pill (the decision *word* is the pill).
- The giant "0.00 inches" headline (replaced by the decision sentence).
- The "Stress risk LOW" chip (derived from confidence + decision).
- The cyan-to-mint confidence bar (replaced by the inline confidence line).
- The four colored top-rail metric cards (replaced by the hairline strip).
- The page-title `H1 Dashboard` (sidebar shows it).
- The topbar duplicate of `Run new analysis` (only the hero card has it now).
- The brand wordmark duplicate (sidebar only).
- The persistent Quick Start sidebar block (demoted to a demo-mode-only section).
- The accent dividers and hero-glow pseudo-elements.

## Run Analysis screen

Single column, max 720px wide, centered.

- Quiet page label top-left (`Run analysis`, 14px ink-muted). Primary action top-right (`Run analysis` button, ink fill, paper text).
- Below: collapsible rows. Each row shows the **currently-selected values** in the closed state. Closed by default if the prior run filled it; open by default if empty.
  - **Field** — name, soil, drainage.
  - **Crop & stage** — corn / soy / potato / alfalfa + emergence / vegetative / flowering / grain fill / maturity.
  - **Conditions** — soil moisture %, last probe age, recent rain.
  - **Irrigation system** — pivot / drip / flood + start time.
- Below that, one collapsed row: **Advanced (researcher overrides)**. The current perpetual validation banner ("Researcher feedback is disabled...") moves inside this section, visible only when expanded.
- Demo-mode scenarios (`Heat wave`, `Balanced day`, `Kimberly Farm`) move into a collapsed `Use a scenario` row, demo-mode only. The freeform textarea moves with them.
- **No duplicate dashboard hero on this screen.** A run-in-progress shows a single inline "Last result: Hold · 79% →" link top-right when a prior result exists, otherwise nothing.
- "Live API mode is not configured / Backend unavailable" right rail removed. State is communicated by the existing demo/live chip in the sidebar.

## Results screen

Same components as the dashboard, in order:

1. **Decision hero** (the new run's result).
2. **Evidence strip** (the inputs the decision was based on).
3. **Why** — bullets in plain English explaining which inputs drove the
   decision (e.g., "Soil moisture is above the trigger threshold of 35%.",
   "Rain forecast Thursday will replenish before stress.").
4. **Inputs** — collapsed by default, read-only echo of the form values.
5. **Technical details** — collapsed by default, raw API response and timing.

No new visual vocabulary. The Results screen is the dashboard hero applied to
a specific run.

## Runs screen (merged History + Saved)

Single page.

- Top: filter pills — `All` · `Saved` · `Last 7 days` · `Apply only` · `Hold only`.
- Below: vertical hairline-separated list. Each row: field · date · decision · inches + a ☆ to save/unsave.
- Click row → Results screen for that run.
- No table chrome (no header row, no zebra striping, no column dividers).

## Settings screen

Vertical stacked sections, label-left / control-right:

- **Account** — email, role.
- **Display** — theme: System / Light / Dark.
- **Backend** — demo-mode toggle, API URL, last connection test.
- **Data** — Export CSV, Delete all runs.

No tabs, no card grid, no "Settings Hub" header.

## Component inventory

Ten components — the entire system:

- `<DecisionHero>` — used on Dashboard and Results.
- `<EvidenceStrip>` — used on Dashboard and Results.
- `<Sidebar>` — desktop nav + footer.
- `<MobileTopbar>` + `<MobileTabBar>`.
- `<CollapsibleRow>` — used in Run Analysis, Settings, Results sub-sections.
- `<RunListRow>` — used in Recent Runs + Runs page.
- `<MetricPopover>` — opened from EvidenceStrip clicks.
- `<Chip>` — demo-mode indicator, filter pills on Runs page.
- `<Button>` — two variants: primary (ink fill) and secondary (ink border).
- `<Field>` — form input wrapper.

The current implementation has dozens of one-off CSS classes (`stacked-card`,
`metric-card`, `spotlight-water`, `decision-pill-apply`, `field-card`,
`tech-details`, etc.). Consolidation to 10 components is itself a meaningful
piece of the sleekening.

## Implementation map

| File | Change |
|---|---|
| `styles.css` | Rewrite. New tokens. ~200 lines deleted. Target ~350 lines. |
| `index.html` | Drop Geist font link. Drop sticky demo-mode banner div. |
| `src/ui/layout.js` | Rewrite sidebar (text-only, 4 items, footer chips). Remove topbar. Add mobile bottom-tab variant. |
| `src/ui/dashboard.js` | Rebuild around 3 zones. Delete giant inches headline, HOLD pill, confidence bar, stress-risk chip, accent dividers. Gate Quick Start behind demo-mode. |
| `src/ui/analysis-form.js` | Convert input groups to collapsible rows. Delete duplicated dashboard hero. Move scenarios behind a demo-only `Use a scenario` row. |
| `src/ui/results.js` | Reuse the hero + evidence-strip components from `dashboard.js` (via `shared.js`). Add `Why` bullets and collapsed `Inputs` / `Technical details`. |
| `src/ui/shared.js` | Extract `renderDecisionHero(...)` and `renderEvidenceStrip(...)` as shared components used by dashboard and results. The only new abstraction. |
| `src/ui/events.js`, `form-state.js`, `analysis-spotlight.js` | Minimal touch. Only what's needed to support collapsible rows. |
| `src/ui/runs.js` (new or refactor) | Merge History + Saved into a filtered Runs page. Delete the duplicated saved-runs path. |

## Verification

- Playwright screenshots at 1920 / 1024 / 768 / 480. All current dashboard
  screenshots (`dashboard-1920.png`, `dashboard-empty.png`,
  `dashboard-populated.png`, `dashboard-hold-validation.png`) are expected to
  change substantially — record new baselines after the redesign lands.
- Visual a11y: every text on `--bg` and `--panel` must clear WCAG AA against
  `--ink` and `--ink-muted`. Run an axe pass.
- Manual: open the dashboard in demo mode → click `Run new analysis` →
  complete the form → see the result → save it → find it in Runs → change
  theme to dark → open on phone-sized viewport. The flow must never present a
  duplicate label, a duplicate CTA, or a metric without a clear answer to
  "what is this telling me."
- Tab order on Run Analysis: top-to-bottom, no skip-back. Phone-keyboard usable.
- Performance: no regression in load time vs current baseline (use the
  `/benchmark` skill to record before/after).

## Out of scope

- Migration to Next.js or any other framework.
- New product features (no new fields, no new metrics, no new run logic).
- Backend changes (the Run Analysis API contract is unchanged).
- Animations beyond the existing fade-in and collapsible expand. No
  micro-interactions, no Lottie, no parallax.

## Open question (carried forward)

- The current sidebar item **Field Ops** has unclear status. Default plan
  removes it. If it is a real future destination, reinstate as a fifth nav
  item; the four-item nav otherwise stays.
