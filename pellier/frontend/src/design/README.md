# Pellier design tokens

The token module behind the Pellier frontend. Colors, typography, spacing, shadows, radii, animation timing, breakpoints, and fluid layout values are defined once in `tokens.ts` and extended into the Tailwind config, which is how most of the application consumes them.

**This module is not the whole design system, and it never was.** The authority on the visual world is the repository-root `DESIGN.md`; the shipped surface contracts live in `observatory/styles/base.css`, `styles/`, `operator/styles/`, and the shared components in `src/shared/`. This file documents `tokens.ts` and the two primitives that are actually mounted.

---

## Color Palette

All color tokens are exported from `tokens.ts` and extended into the Tailwind config.

| Token          | Hex       | Usage                                              |
| -------------- | --------- | -------------------------------------------------- |
| `cream`        | `#f7f3ec` | Page background (warm canvas)                       |
| `sand`         | `#f1ece1` | Recessed and nested surfaces                        |
| `espresso`     | `#1f1410` | Strongest ink and the neutral primary action        |
| `olive`        | `#6B705C` | Material storytelling. Never a proof status         |
| `terracotta`   | `#9a3412` | Storefront warmth and selective brand emphasis      |
| `ink`          | `#1f1410` | Primary text                                        |
| `inkSoft`      | `#3a3833` | Long-form prose                                     |
| `inkQuiet`     | `#6b665d` | Captions, timestamps, secondary metadata            |
| `dusk`         | `#1f1410` | Dark surfaces and hover states                      |
| `creamWarm`    | `#fbf8f2` | Raised paper: cards, panels, fields                 |
| `espressoDark` | `#1f1410` | Dark surface base                                   |
| `espressoMid`  | `#2a2724` | Dark surface mid-tone                               |

These are the values in `tokens.ts`, and they resolve to the same swatches
`DESIGN.md` names. `ink`, `dusk`, `espresso` and `espressoDark` are four names
for one colour; that convergence is deliberate and predates this file.

---

## Typography

Three font families cover all surfaces. Fluid sizing via `clamp()` keeps text proportional across viewport widths without per-breakpoint overrides.

### Font Families

| Role                | Family                    | Fallback Stack          | Weight |
| ------------------- | ------------------------- | ----------------------- | ------ |
| Display / Headlines | Fraunces (variable)       | Georgia, serif          | 400    |
| Body / UI           | Instrument Sans (variable)          | system-ui, sans-serif   | 400    |
| Mono / Code         | JetBrains Mono (variable) | ui-monospace, monospace | 400    |

### Text Utility Classes (`typography.css`)

| Class             | Family         | Size                             | Notes                         |
| ----------------- | -------------- | -------------------------------- | ----------------------------- |
| `.text-display`   | Fraunces       | `clamp(28px, 4vw, 48px)`         | Hero headlines, product names |
| `.text-headline`  | Fraunces       | `clamp(22px, 3vw, 36px)`         | Section headlines             |
| `.text-body`      | Instrument Sans          | `clamp(14px, 1.1vw, 16px)`       | Default body text             |
| `.text-body-sm`   | Instrument Sans          | 13px                             | Small body text, captions     |
| `.text-mono`      | JetBrains Mono | 12px                             | Code, tech footnotes          |
| `.text-eyebrow`   | Instrument Sans          | 10px, uppercase, 0.16em tracking | Category labels               |
| `.text-microcopy` | Instrument Sans          | 11px                             | Fine print, disclaimers       |

---

## Spacing Scale

4px base unit. All values exported from `tokens.ts`.

| Token | Value | Typical Use                |
| ----- | ----- | -------------------------- |
| `xs`  | 4px   | Tight gaps, icon padding   |
| `sm`  | 8px   | Chip padding, small gaps   |
| `md`  | 16px  | Card padding, section gaps |
| `lg`  | 24px  | Section spacing            |
| `xl`  | 32px  | Large section spacing      |
| `2xl` | 48px  | Page section dividers      |
| `3xl` | 64px  | Hero section padding       |

---

## Shadow Tokens

Warm-tinted shadows using `rgba(107, 74, 53, ...)` (ink-soft base) for the editorial luxury feel. No cold grey drops.

| Token | Value                                                               | Usage                  |
| ----- | ------------------------------------------------------------------- | ---------------------- |
| `sm`  | `0 2px 8px rgba(107,74,53,0.06), 0 1px 3px rgba(107,74,53,0.04)`    | Subtle card elevation  |
| `md`  | `0 4px 16px rgba(107,74,53,0.08), 0 2px 6px rgba(107,74,53,0.05)`   | Default card shadow    |
| `lg`  | `0 8px 24px rgba(107,74,53,0.10), 0 4px 8px rgba(107,74,53,0.06)`   | Elevated cards, modals |
| `xl`  | `0 24px 48px rgba(107,74,53,0.14), 0 8px 16px rgba(107,74,53,0.08)` | Hero elements, drawers |

---

## Border Radii

| Token  | Value  | Usage                        |
| ------ | ------ | ---------------------------- |
| `sm`   | 8px    | Chips, pills, small elements |
| `md`   | 12px   | Cards, inputs                |
| `lg`   | 16px   | Modals, large cards          |
| `xl`   | 24px   | Hero elements                |
| `full` | 9999px | Avatars, circular buttons    |

---

## Animation Timing

| Token    | Duration                    | Easing   | Usage                             |
| -------- | --------------------------- | -------- | --------------------------------- |
| `slide`  | 240ms                       | ease-out | Drawer open/close, panel slides   |
| `fade`   | 180ms                       | ease-out | Opacity transitions, hover states |
| `spring` | stiffness: 320, damping: 28 | —        | Framer Motion spring animations   |

All animated primitives respect `prefers-reduced-motion` by disabling or reducing to opacity-only transitions.

---

## Responsive Breakpoints

Two breakpoints define three layout bands. Content is fluid within each band.

| Token            | Value  | Band Below                                                   | Band Above                                                          |
| ---------------- | ------ | ------------------------------------------------------------ | ------------------------------------------------------------------- |
| `mobile`         | 768px  | Mobile (< 768px): single column, bottom nav, stacked layouts | Desktop (768px+): multi-column, persistent sidebar                  |
| `wide`           | 1440px | Desktop (768px - 1440px): 2-3 grid columns, fluid scaling    | Wide (> 1440px): content centers at max-width, extra breathing room |
| `expansionStack` | 1280px | Observatory expansion area stacks from 3-col to 2+1 layout       | Full 3-column expansion area                                        |

### Three-Band Layout

- **Mobile** (< 768px): Single-column layouts, bottom navigation, stacked hero, drawer sidebar
- **Desktop** (768px - 1440px): Multi-column grids, persistent sidebar, fluid typography scaling between mobile and wide sizes
- **Wide** (> 1440px): Content stops growing at `maxWidth` (1440px) and centers with `margin: 0 auto`. Wide displays get more breathing room, not more content

---

## Fluid Layout Tokens

Continuous scaling values used via CSS `clamp()` so layouts adapt smoothly across viewport widths rather than snapping at breakpoints.

| Token              | Value                      | Purpose                                           |
| ------------------ | -------------------------- | ------------------------------------------------- |
| `containerPadding` | `clamp(16px, 4vw, 48px)`   | Horizontal padding that breathes on wide displays |
| `displaySize`      | `clamp(28px, 4vw, 48px)`   | Display text scales from mobile to wide           |
| `headlineSize`     | `clamp(22px, 3vw, 36px)`   | Section headlines scale proportionally            |
| `bodySize`         | `clamp(14px, 1.1vw, 16px)` | Body text with intentionally narrow range         |
| `gridCardMin`      | 280px                      | Minimum card width for CSS Grid `auto-fill`       |
| `maxWidth`         | 1440px                     | Content max-width, centers on ultra-wide          |

> **Body text narrow range:** The 2px range (`14px` to `16px`) is intentional. Reading distance doesn't change meaningfully between 14-inch and 16-inch laptops, so body text stays near-constant while display type does the scaling work.

---

## Primitives

Two primitives live in `src/design/primitives/` and are re-exported from
`primitives/index.ts`. Both are mounted by `components/Header.tsx`.

Nine others once sat beside them — Button, Card, Chip, Input, Modal, Drawer,
Pill, Sidebar, Timeline — fully written, fully exported, and imported by
nothing. They have been removed. If you need a control the two below do not
cover, take the pattern from the surface stylesheet that already draws it
rather than reviving a parallel one here.

### Avatar

Circular monogram display.

- **Sizes:** `sm`, `md`, `lg`
- **Key props:** `initial` (single character), `bgColor`, `size`

### IconButton

Circular ghost button for icon-only actions (header, toolbars).

- **Sizes:** `sm` (32px), `md` (44px, the touch floor)
- **Key props:** `icon`, `size`, `ariaLabel`, `onClick`
- Includes a visible focus indicator, and does not shrink as a flex item

---

## Notes

- The `expansionStack` token (1280px) defines where the Observatory three-column expansion area transitions from 3 equal columns to a 2+1 stacked layout. This is separate from the `mobile` breakpoint.
- The body text narrow `clamp()` range (14px to 16px) is intentional — reading distance doesn't change meaningfully between laptop sizes, so body text stays near-constant while display type does the scaling work.
