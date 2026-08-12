# Design

Visual system for Jellyscope. See PRODUCT.md for register, users, and
principles. The guiding reference is Aladin Lite: canvas-first, minimal
floating chrome, monospace numerics, near-black palette, one restrained accent.

## Theme

Dark, neutral "observatory" — a near-black slate that never competes with the
scientific colormaps (Viridis/Inferno/…) or the RGB composite. Single restrained
blue accent for selection, primary action, and focus.

## Color

Tokens are OKLCH (Tailwind theme, `frontend/tailwind.config.ts`). The Plotly
canvas theme mirrors these as hex in `src/jellyscope/visualization/_viz_helpers.py`
so the plot area sits in the same slate as the chrome.

| Token | OKLCH | ~hex | Role |
|-------|-------|------|------|
| `bg` | `0.16 0.004 260` | `#0d0d0f` | canvas void / app backdrop |
| `surface-1` | `0.21 0.005 260` | `#17181b` | toolbar, rail |
| `surface-2` | `0.26 0.006 260` | `#212328` | inputs, hover wells |
| `border` | `0.32 0.006 260` | `#2f3138` | hairlines, faint grid |
| `ink` | `0.93 0.004 260` | `#e8e8ea` | primary text |
| `ink-dim` | `0.72 0.008 260` | `#a2a3a8` | labels, secondary |
| `accent` | `0.70 0.15 250` | `#4a9eff` | selection, primary action, focus ring |
| `accent-quiet` | `accent / 0.15` | — | selected-row wash |
| `disk` | `0.80 0.16 150` | — | disk-clump badge |
| `outside` | `0.80 0.14 75` | — | outside-clump badge |
| `danger` | `0.63 0.20 25` | `#ff5c5c` | selected-clump boundary overlay |

Overlay colors (clump boundaries/centroids) are duplicated by necessity in
`frontend/src/theme.ts` and `src/jellyscope/visualization/image_viewer.py`
(`_RED`/`_BLUE`/`_WHITE`); change both together.

## Typography

- **IBM Plex Sans** (400/500/600) for all UI text.
- **IBM Plex Mono** (400/500) for every numeric — RA/Dec, wavelengths, areas,
  R_eff, clump IDs, the coordinate readout. Applied via the `.tabular` utility
  (`font-mono` + `tnum`).
- Loaded from Google Fonts over HTTPS (mixed-content safe).
- Fixed rem scale, ~1.2 ratio: `xs .6875` / `sm .75` / `base .8125` /
  `md .9375` / `lg 1.0625` rem.

## Layout

Hybrid canvas-first (`frontend/src/components/App.tsx`):

- The datacube (`#galaxy-viewer`, Plotly) fills the viewport.
- **Floating toolbar** top-left: `.glass` panel (translucent `surface-1` +
  backdrop-blur — the one purposeful glass use, floating over live data). Holds
  the wordmark chip then labeled clusters: Source · View · Tools · Overlays.
  The View cluster swaps Single vs RGB controls in place.
- **Docked right rail** ("Inspector"): a header with a collapse toggle, then
  Properties → Separations → Clumps. Resizable (drag handle writes
  `--sidebar-w`), collapsible to full-screen the canvas.
- **Coordinate readout** floats bottom-left, monospace, `aria-live`.
- **Loading bar** sweeps the top edge during a figure fetch.
- z-index scale: canvas 0 · overlay 10 · rail 20 · toolbar 30 · dropdown 40.

## Components

Shared primitives in `frontend/src/components/ui.tsx` (Cluster, Divider, Select,
Btn, Segmented). Every interactive element carries default / hover /
focus-visible / active / disabled; toggles and clump rows add a selected state.
Clump-row selection = `accent-quiet` wash + a leading accent dot (no side-stripe
border). Badges use a 1px inset ring in the `disk`/`outside` hue.

Empty states teach rather than say "nothing here": Properties → "Click a clump…";
Separations → "Select ≥2 clumps to measure their angular separations."

## Motion

Functional only. 120–200ms ease-out transitions on panels, buttons, selection;
figure swaps crossfade via `Plotly.react`; selection recolor is instant. Full
`prefers-reduced-motion: reduce` alternative collapses everything to instant
(`frontend/src/styles.css`).

## Build

Vite + TypeScript + Preact + Tailwind under `frontend/`. `vite build` emits a
hashed bundle + manifest into `src/jellyscope/web/static/dist`; the Jinja shell
(`web/templates/index.html`) resolves assets from the manifest (or the Vite dev
server when `JELLYSCOPE_VITE_DEV` is set) and injects a `bootstrap` JSON block.
The Plotly interaction core (zoom/pan/WCS/RGB-snap) is a typed, framework-free
module under `frontend/src/viewer/`.
