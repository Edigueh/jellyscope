# Frontend

The Jellyscope frontend is a single-page application built with vanilla HTML, CSS, and JavaScript, using Plotly.js for all interactive visualizations. No frontend framework is needed.

**Files covered**:

- [web/templates/index.html](../src/jellyscope/web/templates/index.html) — HTML structure
- [web/static/app.js](../src/jellyscope/web/static/app.js) — JavaScript controller
- [web/static/style.css](../src/jellyscope/web/static/style.css) — Dark theme CSS

---

## index.html — Page Structure

**Location**: `src/jellyscope/web/templates/index.html`

This is a Jinja2 template rendered by FastAPI (via `Jinja2Templates`). It receives two variables from the server:

- `datacubes`: list of available datacube names (e.g., `["nircam", "nircam_matched"]`)
- `filters`: list of filter names (e.g., `["F070W", "F090W", ...]`)

### Layout

The page uses CSS Grid with two columns:

```plaintext
┌──────────────────────────────────────────────────────────┐
│  HEADER: "Jellyscope — JWST Jellyfish Galaxy Explorer"   │
├──────────────────────────────┬───────────────────────────┤
│                              │  PROPERTIES PANEL         │
│  VIEWER CONTROLS             │  (clump info table)       │
│  [Datacube ▼] [Slider]       ├───────────────────────────┤
│  [Colors ▼] [Pan|Rect|Lasso] │  CLUMP LIST               │
│                              │  (checkboxes with badges) │
│  GALAXY VIEWER               │  [Filter: All ▼]          │
│  (Plotly heatmap)            ├───────────────────────────┤
│  172 x 221 px image          │  SPECTRUM PLOT (SED)      │
│  with clump overlays         │  (Plotly line chart)      │
│                              │                           │
└──────────────────────────────┴───────────────────────────┘
```

Left column: `1fr` (flexible) — the galaxy viewer expands to fill available space.
Right column: `360px` fixed — the three panels stack vertically.

### Key HTML Elements

| Element ID | Type | Purpose |
| ----------- | ------ | --------- |
| `datacube-select` | `<select>` | Choose between nircam / nircam_matched |
| `filter-slider` | `<input type="range">` | Navigate 20 filter channels (0-19) |
| `filter-label` | `<span>` | Shows current filter name (e.g., "F200W") |
| `colorscale-select` | `<select>` | Viridis, Inferno, Plasma, Cividis, Hot, Greys |
| `btn-click` / `btn-select` / `btn-lasso` | `<button>` | Interaction mode buttons |
| `galaxy-viewer` | `<div>` | Plotly mounts the heatmap here |
| `properties-content` | `<div>` | Clump properties table or status message |
| `clump-filter` | `<select>` | Filter clump list: All / Disk / Outside |
| `clump-list` | `<div>` | Dynamic clump list with checkboxes |
| `spectrum-plot` | `<div>` | Plotly mounts the SED chart here |

### Jinja2 Template Variables

```html
<!-- Datacube dropdown populated from server -->
{% for dc in datacubes %}
<option value="{{ dc }}">{{ dc }}</option>
{% endfor %}

<!-- Filter slider range from server -->
<input type="range" min="0" max="{{ filters|length - 1 }}" value="7">

<!-- Filter names passed to JavaScript -->
<script>
    const FILTERS = {{ filters | tojson }};
    // → ["F070W", "F090W", ..., "F480M"]
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
    dragmode: "pan",              // Plotly interaction mode
    clumps: [],                   // Loaded clump list from API
};
```

### Initialization Flow

```plaintext
DOMContentLoaded
    └── init()
        ├── loadClumpList()    → GET /api/clumps → populate clump list
        ├── renderViewer()     → GET /api/viewer/nircam/7 → render Plotly figure
        └── setupEventListeners()
            ├── datacube-select → onChange → renderViewer()
            ├── filter-slider   → onInput → update label + renderViewer()
            ├── colorscale-select → onChange → renderViewer()
            ├── mode buttons    → onClick → Plotly.relayout(dragmode)
            └── clump-filter    → onChange → loadClumpList()
```

### Function Reference

#### `init()`

Async entry point. Called on `DOMContentLoaded`. Loads the clump list, renders the initial viewer, and attaches all event listeners.

#### `setupEventListeners()`

Attaches DOM event handlers to all control elements. Each handler updates `state` and triggers the appropriate re-render.

#### `renderViewer()`

The core render function. Fetches the Plotly figure from the API and renders it:

```plaintext
1. Build URL: /api/viewer/{datacube}/{channel}?selected={ids}&colorscale={scale}
2. fetch(url) → JSON response with figure dict
3. Set figure.layout.dragmode = state.dragmode
4. Plotly.react("galaxy-viewer", fig.data, fig.layout, plotlyConfig)
5. Attach plotly_click and plotly_selected event handlers
```

Called whenever: datacube changes, filter changes, colorscale changes, or clump selection changes.

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
