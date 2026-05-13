# Frontend

The Jellyscope frontend is a single-page application built with vanilla HTML, CSS, and JavaScript, using Plotly.js for all interactive visualizations. No frontend framework is needed.

**Files covered**:

- [web/templates/index.html](../src/jellyscope/web/templates/index.html) — HTML structure
- [web/static/app.js](../src/jellyscope/web/static/app.js) — JavaScript controller
- [web/static/style.css](../src/jellyscope/web/static/style.css) — Dark theme CSS

---

## index.html — Page Structure

**Location**: `src/jellyscope/web/templates/index.html`

This is a Jinja2 template rendered by FastAPI (via `Jinja2Templates`). It receives three variables from the server:

- `datacubes`: list of available datacube names (e.g., `["nircam", "nircam_matched"]`)
- `filters`: list of filter names (e.g., `["F070W", "F090W", ...]`)
- `wavelengths`: dict mapping filter names to central wavelengths in µm

### Layout

The page uses CSS Grid with two columns:

```plaintext
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER: "Jellyscope — JWST Jellyfish Galaxy Explorer"               │
├────────────────────────────────────────┬─────────────────────────────┤
│                                        │  PROPERTIES PANEL           │
│  VIEWER CONTROLS                       │  (clump info table)         │
│  [Datacube ▼] [Stretch ▼]             ├─────────────────────────────┤
│  [Single|RGB] [Filter/RGB controls]    │  CLUMP LIST                 │
│  [Pan|Rect|Lasso] [Centroids]          │  (checkboxes with badges)   │
│                                        │  [Filter: All ▼]            │
│  GALAXY VIEWER                         │                             │
│  (Plotly heatmap or RGB image)         │                             │
│  172 x 221 px image                    │                             │
│  with clump overlays                   │                             │
│                                        │                             │
└────────────────────────────────────────┴─────────────────────────────┘
```

Left column: `1fr` (flexible) — the galaxy viewer expands to fill available space.
Right column: `360px` fixed — the panels stack vertically.

### Key HTML Elements

| Element ID | Type | Purpose |
| ----------- | ------ | --------- |
| `datacube-select` | `<select>` | Choose between nircam / nircam_matched |
| `stretch-select` | `<select>` | Intensity stretch: Log, Asinh (Lupton), Power |
| `btn-view-single` / `btn-view-rgb` | `<button>` | Toggle between single-band and RGB mode |
| `filter-slider` | `<input type="range">` | Navigate 20 filter channels (0-19) — single mode only |
| `colorscale-select` | `<select>` | Viridis, Inferno, Plasma, Cividis, Hot, Greys — single mode only |
| `rgb-r` / `rgb-g` / `rgb-b` | `<select>` | Filter channel for each RGB band — RGB mode only |
| `rgb-q` | `<input type="range">` | Softening (Q) parameter for Lupton stretch — RGB mode only |
| `rgb-q-label` | `<span>` | Shows current Q value |
| `filter-label` | `<span>` | Unified status: filter name (single) or R/G/B combo (RGB) |
| `btn-click` / `btn-select` / `btn-lasso` | `<button>` | Interaction mode buttons |
| `btn-centroids` | `<button>` | Toggle centroid markers visibility |
| `galaxy-viewer` | `<div>` | Plotly mounts the figure here |
| `properties-content` | `<div>` | Clump properties table or status message |
| `clump-filter` | `<select>` | Filter clump list: All / Disk / Outside |
| `clump-list` | `<div>` | Dynamic clump list with checkboxes |

### Jinja2 Template Variables

```html
<!-- Datacube dropdown populated from server -->
{% for dc in datacubes %}
<option value="{{ dc }}">{{ dc }}</option>
{% endfor %}

<!-- Filter slider range from server -->
<input type="range" min="0" max="{{ filters|length - 1 }}" value="7">

<!-- Filter names and wavelengths passed to JavaScript -->
<script>
    const FILTERS = {{ filters | tojson }};
    // → ["F070W", "F090W", ..., "F480M"]
    const WAVELENGTHS = {{ wavelengths | tojson }};
    // → {"F070W": 0.704, "F090W": 0.901, ...}
</script>
```

---

## app.js — JavaScript Controller

**Location**: `src/jellyscope/web/static/app.js`

### Application State

All UI state is tracked in a single global object:

```javascript
const state = {
    datacube: "nircam",           // Currently selected datacube
    channel: 7,                   // Current filter channel (default: F200W)
    selectedClumps: new Set(),    // Set of selected clump IDs
    colorscale: "Viridis",        // Current colorscale
    stretch: "log",               // Intensity stretch function
    dragmode: "pan",              // Plotly interaction mode
    clumps: [],                   // Loaded clump list from API
    showCentroids: false,         // Whether centroid markers are visible
    viewMode: "single",           // "single" (heatmap) or "rgb" (composite)
    rgbR: 19,                     // Red channel filter index (longest λ)
    rgbG: 10,                     // Green channel filter index (middle λ)
    rgbB: 0,                      // Blue channel filter index (shortest λ)
    rgbQ: 8.0,                    // Lupton softening parameter
};
```

### Initialization Flow

```plaintext
DOMContentLoaded
    └── init()
        ├── populateRGBSelects()  → fill R/G/B dropdowns with filter names + wavelengths
        ├── loadClumpList()       → GET /api/clumps → populate clump list
        ├── updateFilterLabel()   → set initial status label
        ├── renderViewer()        → GET /api/viewer/... → render Plotly figure
        └── setupEventListeners()
            ├── datacube-select    → onChange → renderViewer()
            ├── filter-slider      → onInput → updateFilterLabel() + renderViewer()
            ├── colorscale-select  → onChange → renderViewer()
            ├── stretch-select     → onChange → renderViewer()
            ├── view-btn (Single/RGB) → onClick → updateViewModeUI() + renderViewer()
            ├── rgb-r/g/b          → onChange → updateFilterLabel() + renderViewer()
            ├── rgb-q              → onInput → debounced(renderViewer, 300ms)
            ├── mode buttons       → onClick → Plotly.relayout(dragmode)
            ├── btn-centroids      → onClick → toggle + renderViewer()
            └── clump-filter       → onChange → loadClumpList()
```

### Function Reference

#### `init()`

Async entry point. Called on `DOMContentLoaded`. Loads the clump list, renders the initial viewer, and attaches all event listeners.

#### `setupEventListeners()`

Attaches DOM event handlers to all control elements. Each handler updates `state` and triggers the appropriate re-render.

#### `debounce(fn, ms)`

Utility that delays function execution until `ms` milliseconds after the last invocation. Used for the Q slider to avoid flooding the API during drag.

#### `populateRGBSelects()`

Fills the R/G/B `<select>` dropdowns with filter options (name + wavelength labels). Sets default values: longest wavelength → R, middle → G, shortest → B.

#### `updateFilterLabel()`

Updates the `#filter-label` status indicator:
- **Single mode**: shows `"F200W (1.99 µm)"`
- **RGB mode**: shows `"R:F480M  G:F277W  B:F070W"`

#### `updateViewModeUI()`

Shows/hides the appropriate control group (`#single-controls` vs `#rgb-controls`) based on `state.viewMode`.

#### `renderViewer()`

The core render function. Fetches the Plotly figure from the API and renders it:

```plaintext
1. If viewMode == "rgb":
     Build URL: /api/viewer/{datacube}/rgb?r={R}&g={G}&b={B}&softening={Q}&selected={ids}
   Else:
     Build URL: /api/viewer/{datacube}/{channel}?selected={ids}&colorscale={scale}&stretch={stretch}
2. fetch(url) → JSON response with figure dict
3. Set figure.layout.dragmode = state.dragmode
4. If !showCentroids → remove last trace (centroids) from data
5. Plotly.react("galaxy-viewer", fig.data, fig.layout, plotlyConfig)
6. Attach plotly_click event handler
```

Called whenever: datacube changes, filter changes, colorscale changes, stretch changes, view mode changes, RGB channels change, Q slider moves (debounced), clump selection changes, or centroids toggled.

#### `onViewerClick(eventData)`

Handles clicks on the galaxy image:

1. Extract `(x, y)` pixel coordinates from the clicked point
2. `GET /api/pixel/{x}/{y}/clump` — check if pixel belongs to a clump
3. If clump found → `toggleClumpSelection(clumpId)`
4. If no clump → `showPixelSpectrum(x, y)`

#### `onViewerSelected(eventData)`

Handles Plotly lasso/rectangle selection events:

1. Extract pixel coordinates from all selected points
2. Filter to only heatmap points (`curveNumber === 0`)
3. `POST /api/region/spectrum/{datacube}` with pixel list
4. Render the returned SED figure in the spectrum panel

#### `toggleClumpSelection(clumpId)`

Toggles a clump in/out of `state.selectedClumps`:

- **0 selected**: clear all panels
- **1 selected**: show that clump's properties + SED
- **2+ selected**: show multi-clump SED comparison

Also calls `renderViewer()` to update boundary highlighting (selected = red).

#### `showClumpDetails(clumpId)`

Fetches properties and spectrum for a single clump in parallel:

```javascript
const [propsResp, specResp] = await Promise.all([
    fetch(`/api/clumps/${clumpId}`),
    fetch(`/api/clumps/${clumpId}/spectrum/${state.datacube}`),
]);
```

Updates both the properties panel (HTML table) and spectrum plot (Plotly figure).

#### `showMultiClumpComparison(clumpIds)`

Sends clump IDs to the comparison endpoint and renders the overlaid SED figure.

#### `showPixelSpectrum(x, y)`

Fetches and displays the SED for a single pixel (when clicked outside any clump).

#### `loadClumpList()`

Fetches the clump list from the API (with optional component filter) and calls `renderClumpList()`.

#### `renderClumpList()`

Generates HTML for the clump list panel. Each item has:

- A checkbox for multi-selection
- The clump ID
- A colored badge showing component (`disk` = green, `outside` = orange)
- Pixel count

```html
<div class="clump-item selected" onclick="toggleClumpSelection(4)">
    <input type="checkbox" checked>
    <span>Clump 4</span>
    <span class="clump-badge disk">disk</span>
    <span>144px</span>
</div>
```

#### `updateClumpListUI()`

Updates checkbox states and selected styling without re-rendering the entire list.

#### `showPropertiesMessage(msg)` / `clearPanels()`

Helper functions for updating/clearing the properties and spectrum panels.

### Plotly Events Used

| Event | When | Action |
| ------- | ------ | -------- |
| `plotly_click` | User clicks on the heatmap | Identify clump or show pixel spectrum |
| `plotly_selected` | User finishes lasso/rectangle | Extract region spectrum |

### Plotly Configuration

```javascript
const plotlyConfig = {
    responsive: true,                                  // Resize with container
    displayModeBar: true,                              // Show toolbar
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    scrollZoom: true,                                  // Zoom with mouse wheel
};
```

---

## style.css — Dark Theme

**Location**: `src/jellyscope/web/static/style.css`

### CSS Custom Properties (Variables)

```css
:root {
    --bg-primary: #0f0f23;       /* Darkest background (main area) */
    --bg-secondary: #16213e;     /* Header and control bars */
    --bg-panel: #1a1a2e;         /* Panel backgrounds */
    --text-primary: #e0e0e0;     /* Main text */
    --text-secondary: #999;      /* Labels, secondary text */
    --accent: #00ccff;           /* Cyan accent (titles, highlights) */
    --accent-hover: #33ddff;     /* Lighter accent for hover */
    --border: #2a2a4a;           /* Borders and dividers */
    --danger: #ff4444;           /* Selected clump highlight */
}
```

### Grid Layout

```css
main {
    display: grid;
    grid-template-columns: 1fr 360px;   /* Flexible left, fixed 360px right */
    height: calc(100vh - 41px);          /* Full height minus header */
}
```

### Customization Guide

**Change the accent color**:

```css
:root { --accent: #ff6600; }   /* Orange theme */
```

**Change the right panel width**:

```css
main { grid-template-columns: 1fr 450px; }
```

**Light theme** (override all `--bg-*` and `--text-*` variables):

```css
:root {
    --bg-primary: #ffffff;
    --bg-secondary: #f5f5f5;
    --bg-panel: #fafafa;
    --text-primary: #333333;
    --text-secondary: #666666;
    --border: #dddddd;
}
```

### Component Badges

Clumps are color-coded by component:

- **Disk clumps**: Green border and text (`#44ff44`)
- **Outside clumps**: Orange border and text (`#ffaa00`)

```css
.clump-badge.disk    { color: #44ff44; border: 1px solid #44ff44; }
.clump-badge.outside { color: #ffaa00; border: 1px solid #ffaa00; }
```

### View Mode Buttons and Toggle Buttons

View mode (`Single` / `RGB`) and interaction mode buttons share styling patterns:

```css
.view-btn, .mode-btn, .toggle-btn {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    /* Active state: cyan background, black text */
}
.view-btn.active, .mode-btn.active, .toggle-btn.active {
    background: var(--accent);
    color: #000;
}
```

### RGB Controls

The Q slider and its label are styled to match the filter slider:

```css
#rgb-q {
    width: 80px;
    accent-color: var(--accent);
}
#rgb-q-label {
    color: var(--accent);
    font-weight: 600;
}
```
