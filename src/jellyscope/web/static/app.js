/**
 * Jellyscope — Frontend controller
 * Manages state, API calls, Plotly rendering, and user interactions.
 */

function debounce(fn, ms) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), ms);
    };
}

const DEFAULT_RGB_FILTERS = {r: "F200W", g: "F115W", b: "F090W"};

// Fallback wavelength offsets (µm) used when a default filter lacks a
// WAVELENGTHS entry on first load. Values match F200W−F115W and F115W−F090W.
const RGB_DELTA_RG_FALLBACK = 0.836;
const RGB_DELTA_GB_FALLBACK = 0.253;

// Resolve {r, g, b} indices into filterList. Prefers the named DEFAULT_RGB_FILTERS
// when both filterList and WAVELENGTHS know them. For any unresolved slot, picks
// by λ-rank against the sublist of indices with a known wavelength: R = argmax(λ),
// B = argmin(λ), G = argmin |λ − (λ_R + λ_B) / 2|. Falls back to position
// (length-1, mid, 0) only when fewer than three filters carry a wavelength.
// Lookup index of each named default; require both presence in filterList AND
// a known wavelength. Returns -1 for unresolved slots.
function resolveNamedRgb(filterList) {
    const lookup = (key) => {
        const i = filterList.indexOf(DEFAULT_RGB_FILTERS[key]);
        return (i >= 0 && WAVELENGTHS[DEFAULT_RGB_FILTERS[key]] != null) ? i : -1;
    };
    return {r: lookup("r"), g: lookup("g"), b: lookup("b")};
}

// All filters with a known wavelength, sorted ascending by λ.
function knownWavelengths(filterList) {
    const known = [];
    filterList.forEach((name, i) => {
        const wl = WAVELENGTHS[name];
        if (wl != null) known.push({i, wl});
    });
    known.sort((a, b) => a.wl - b.wl);
    return known;
}

// argmin distance to target.
function nearestKnownToWl(known, targetWl) {
    let best = known[0];
    let bestDist = Infinity;
    for (const k of known) {
        const d = Math.abs(k.wl - targetWl);
        if (d < bestDist) {
            best = k;
            bestDist = d;
        }
    }
    return best;
}

// Position-only fallback when fewer than 3 filters carry a wavelength.
function positionFallback(result, filterList) {
    return {
        r: result.r >= 0 ? result.r : Math.max(0, filterList.length - 1),
        g: result.g >= 0 ? result.g : Math.floor(filterList.length / 2),
        b: Math.max(result.b, 0),
    };
}

function resolveRgbDefaults(filterList) {
    const result = resolveNamedRgb(filterList);
    if (result.r >= 0 && result.g >= 0 && result.b >= 0) return result;

    const known = knownWavelengths(filterList);
    if (known.length < 3) return positionFallback(result, filterList);

    const lo = known[0];
    const hi = known.at(-1);
    const midPick = nearestKnownToWl(known, (lo.wl + hi.wl) / 2);

    if (result.r < 0) result.r = hi.i;
    if (result.b < 0) result.b = lo.i;
    if (result.g < 0) result.g = midPick.i;
    return result;
}

// Filter state is recomputed when the dataset/datacube changes — keep
// the active filter list in module scope so the rest of the code can
// reference it without rereading the DOM. Initialized from the
// server-injected FILTERS constant, refreshed via the filters endpoint.
let currentFilters = FILTERS.slice();

const _initialRgb = resolveRgbDefaults(currentFilters);

const state = {
    dataset: DEFAULT_DATASET,
    datacube: DEFAULT_DATACUBE,
    channel: 7, // F200W default
    selectedClumps: new Set(),
    colorscale: "Viridis",
    stretch: "lupton_asinh",
    dragmode: "pan",
    clumps: [],
    showCentroids: false,
    showBoundaries: true,
    viewMode: "single", // "single" or "rgb"
    rgbR: _initialRgb.r,
    rgbG: _initialRgb.g,
    rgbB: _initialRgb.b,
    // Wavelength offsets (µm) locked at datacube load. Anchor changes snap
    // the other two slots to the filters nearest λ_anchor ± these Δs.
    rgbDeltaRG: null,
    rgbDeltaGB: null,
    rgbQ: 8,
    rgbMethod: "percentile_asinh",
};

function dsBase() {
    return `/api/datasets/${encodeURIComponent(state.dataset)}`;
}

// Refetch datacubes + filters for the active dataset and rebuild
// dependent UI. Clears selection and re-renders viewer + clump list.
async function onDatasetChanged() {
    const dcResp = await fetch(`${dsBase()}/datacubes`);
    const dcData = await dcResp.json();
    const datacubes = dcData.datacubes;
    const dcSel = document.getElementById("datacube-select");
    dcSel.innerHTML = "";
    for (const dc of datacubes) {
        const opt = document.createElement("option");
        opt.value = dc;
        opt.textContent = dc;
        dcSel.appendChild(opt);
    }
    state.datacube = datacubes.includes(state.datacube) ? state.datacube : datacubes[0];
    dcSel.value = state.datacube;

    const fResp = await fetch(`${dsBase()}/filters/${state.datacube}`);
    const fData = await fResp.json();
    currentFilters = fData.filters.map((f) => f.name);

    // Slider bounds may have changed — clamp channel.
    const slider = document.getElementById("filter-slider");
    slider.max = String(Math.max(0, currentFilters.length - 1));
    if (state.channel >= currentFilters.length) state.channel = 0;
    slider.value = String(state.channel);

    // Rebuild RGB selects against new filter list.
    rebuildRGBSelects();

    // Stale selection ids are meaningless across datasets.
    state.selectedClumps.clear();

    updateFilterLabel();
    await loadClumpList();
    await renderViewer();
}

function rebuildRGBSelects() {
    const selects = ["rgb-r", "rgb-g", "rgb-b"];
    // Re-derive defaults against the currently-loaded filter set.
    const resolved = resolveRgbDefaults(currentFilters);
    state.rgbR = resolved.r;
    state.rgbG = resolved.g;
    state.rgbB = resolved.b;
    const defaults = [state.rgbR, state.rgbG, state.rgbB];
    selects.forEach((id, idx) => {
        const sel = document.getElementById(id);
        sel.innerHTML = "";
        currentFilters.forEach((name, i) => {
            const opt = document.createElement("option");
            opt.value = i;
            const wl = WAVELENGTHS[name];
            opt.textContent = wl ? `${name} (${wl} µm)` : name;
            if (i === defaults[idx]) opt.selected = true;
            sel.appendChild(opt);
        });
    });
    captureRgbDeltas();
    snapRgbFromAnchor("R");
    syncRgbSelects();
}

const plotlyConfig = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    scrollZoom: false,
};

// Initialization.

async function init() {
    populateRGBSelects();
    await loadClumpList();
    updateFilterLabel();
    updateRGBMethodUI();
    await renderViewer();
    setupEventListeners();
}

function populateRGBSelects() {
    const selects = ["rgb-r", "rgb-g", "rgb-b"];
    const defaults = [state.rgbR, state.rgbG, state.rgbB];
    selects.forEach((id, idx) => {
        const sel = document.getElementById(id);
        currentFilters.forEach((name, i) => {
            const opt = document.createElement("option");
            opt.value = i;
            const wl = WAVELENGTHS[name];
            opt.textContent = wl ? `${name} (${wl} µm)` : name;
            if (i === defaults[idx]) opt.selected = true;
            sel.appendChild(opt);
        });
    });
    captureRgbDeltas();
    snapRgbFromAnchor("R");
    syncRgbSelects();
}

// Capture the locked wavelength offsets ΔRG = λ_R − λ_G and ΔGB = λ_G − λ_B
// from the currently selected R/G/B triplet. Called once per datacube load.
// If either Δ is non-positive or unresolvable (degenerate or unsorted default
// triplet), fall back to BOTH F200W/F115W/F090W constants — partial fallback
// would mix scales from different sources.
function captureRgbDeltas() {
    const wlR = WAVELENGTHS[currentFilters[state.rgbR]];
    const wlG = WAVELENGTHS[currentFilters[state.rgbG]];
    const wlB = WAVELENGTHS[currentFilters[state.rgbB]];
    const dRG = (wlR != null && wlG != null) ? (wlR - wlG) : null;
    const dGB = (wlG != null && wlB != null) ? (wlG - wlB) : null;
    if (dRG != null && dGB != null && dRG > 0 && dGB > 0) {
        state.rgbDeltaRG = dRG;
        state.rgbDeltaGB = dGB;
    } else {
        state.rgbDeltaRG = RGB_DELTA_RG_FALLBACK;
        state.rgbDeltaGB = RGB_DELTA_GB_FALLBACK;
    }
}

// argmin over currentFilters of |λ − targetWl|. Filters without a WAVELENGTHS
// entry are skipped. Returns the supplied fallback index if none qualify.
function nearestFilterIndex(targetWl, fallbackIndex) {
    let best = -1;
    let bestDist = Infinity;
    currentFilters.forEach((name, i) => {
        const wl = WAVELENGTHS[name];
        if (wl == null) return;
        const d = Math.abs(wl - targetWl);
        if (d < bestDist) {
            best = i;
            bestDist = d;
        }
    });
    return best >= 0 ? best : fallbackIndex;
}

// Anchor in {"R","G","B"}. Snaps the two non-anchor slots to the filters
// nearest the locked-offset targets relative to the anchor's wavelength.
function snapRgbFromAnchor(anchor) {
    const anchorIdx = state["rgb" + anchor];
    const wlAnchor = WAVELENGTHS[currentFilters[anchorIdx]];
    if (wlAnchor == null) return;  // anchor has no λ — nothing to snap to.

    const dRG = state.rgbDeltaRG;
    const dGB = state.rgbDeltaGB;

    if (anchor === "R") {
        state.rgbG = nearestFilterIndex(wlAnchor - dRG, state.rgbG);
        state.rgbB = nearestFilterIndex(wlAnchor - dRG - dGB, state.rgbB);
    } else if (anchor === "G") {
        state.rgbR = nearestFilterIndex(wlAnchor + dRG, state.rgbR);
        state.rgbB = nearestFilterIndex(wlAnchor - dGB, state.rgbB);
    } else if (anchor === "B") {
        state.rgbG = nearestFilterIndex(wlAnchor + dGB, state.rgbG);
        state.rgbR = nearestFilterIndex(wlAnchor + dGB + dRG, state.rgbR);
    }
}

// Sync the three <select>.value to the current state. Re-enables every
// option (the locked-Δ snap rule means no option needs to be disabled).
function syncRgbSelects() {
    const ids = {"rgb-r": state.rgbR, "rgb-g": state.rgbG, "rgb-b": state.rgbB};
    for (const id of Object.keys(ids)) {
        const sel = document.getElementById(id);
        if (!sel) continue;
        for (const opt of sel.options) opt.disabled = false;
        sel.value = String(ids[id]);
    }
}

function setupEventListeners() {
    document.getElementById("dataset-select").addEventListener("change", async (e) => {
        state.dataset = e.target.value;
        await onDatasetChanged();
    });

    document.getElementById("datacube-select").addEventListener("change", (e) => {
        state.datacube = e.target.value;
        renderViewer();
    });

    document.getElementById("filter-slider").addEventListener("input", (e) => {
        state.channel = Number.parseInt(e.target.value);
        updateFilterLabel();
        renderViewer();
    });

    document.getElementById("colorscale-select").addEventListener("change", (e) => {
        state.colorscale = e.target.value;
        renderViewer();
    });

    document.getElementById("stretch-select").addEventListener("change", (e) => {
        state.stretch = e.target.value;
        renderViewer();
    });

    // View mode toggle (Single / RGB)
    document.querySelectorAll(".view-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".view-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.viewMode = btn.dataset.view;
            updateViewModeUI();
            updateFilterLabel();
            renderViewer();
        });
    });

    // RGB filter selectors
    document.getElementById("rgb-r").addEventListener("change", (e) => {
        state.rgbR = Number.parseInt(e.target.value);
        snapRgbFromAnchor("R");
        syncRgbSelects();
        updateFilterLabel();
        renderViewer();
    });
    document.getElementById("rgb-g").addEventListener("change", (e) => {
        state.rgbG = Number.parseInt(e.target.value);
        snapRgbFromAnchor("G");
        syncRgbSelects();
        updateFilterLabel();
        renderViewer();
    });
    document.getElementById("rgb-b").addEventListener("change", (e) => {
        state.rgbB = Number.parseInt(e.target.value);
        snapRgbFromAnchor("B");
        syncRgbSelects();
        updateFilterLabel();
        renderViewer();
    });

    // RGB method toggle
    document.getElementById("rgb-method").addEventListener("change", (e) => {
        state.rgbMethod = e.target.value;
        updateRGBMethodUI();
        renderViewer();
    });

    // Q slider with debounce
    const debouncedRender = debounce(renderViewer, 300);
    document.getElementById("rgb-q").addEventListener("input", (e) => {
        state.rgbQ = Number.parseFloat(e.target.value);
        document.getElementById("rgb-q-label").textContent = state.rgbQ.toFixed(1);
        debouncedRender();
    });

    // Drag mode buttons
    document.querySelectorAll(".mode-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            const mode = btn.dataset.mode;
            state.dragmode = mode;
            const viewer = document.getElementById("galaxy-viewer");
            Plotly.relayout(viewer, {dragmode: mode});
        });
    });

    document.getElementById("clump-filter").addEventListener("change", loadClumpList);

    document.getElementById("btn-centroids").addEventListener("click", () => {
        state.showCentroids = !state.showCentroids;
        document.getElementById("btn-centroids").classList.toggle("active", state.showCentroids);
        renderViewer();
    });

    document.getElementById("btn-boundaries").addEventListener("click", () => {
        state.showBoundaries = !state.showBoundaries;
        document.getElementById("btn-boundaries").classList.toggle("active", state.showBoundaries);
        renderViewer();
    });

    setupSidebarResizer();
}

// Draggable handle between viewer and right panels. Updates the --sidebar-w
// CSS var; clamps within sane bounds; nudges Plotly to reflow on release so
// the heatmap picks up the new column width.
function setupSidebarResizer() {
    const resizer = document.getElementById("sidebar-resizer");
    if (!resizer) return;
    let dragging = false;

    resizer.addEventListener("mousedown", (e) => {
        dragging = true;
        resizer.classList.add("dragging");
        document.body.style.userSelect = "none";
        e.preventDefault();
    });

    globalThis.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const w = Math.max(260, Math.min(900, window.innerWidth - e.clientX));
        document.documentElement.style.setProperty("--sidebar-w", w + "px");
    });

    globalThis.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        resizer.classList.remove("dragging");
        document.body.style.userSelect = "";
        const viewer = document.getElementById("galaxy-viewer");
        if (viewer) Plotly.Plots.resize(viewer);
    });
}

function updateFilterLabel() {
    const label = document.getElementById("filter-label");
    if (state.viewMode === "rgb") {
        label.textContent = `R:${currentFilters[state.rgbR]}  G:${currentFilters[state.rgbG]}  B:${currentFilters[state.rgbB]}`;
    } else {
        const name = currentFilters[state.channel];
        const wl = WAVELENGTHS[name];
        label.textContent = wl ? `${name} (${wl} µm)` : name;
    }
}

function updateViewModeUI() {
    const singleControls = document.getElementById("single-controls");
    const rgbControls = document.getElementById("rgb-controls");
    if (state.viewMode === "rgb") {
        singleControls.style.display = "none";
        rgbControls.style.display = "flex";
        updateRGBMethodUI();
    } else {
        singleControls.style.display = "flex";
        rgbControls.style.display = "none";
    }
}

// Q only matters for the Lupton method; hide its slider otherwise.
function updateRGBMethodUI() {
    const qWrap = document.getElementById("rgb-q-wrap");
    if (!qWrap) return;
    qWrap.style.display = state.rgbMethod === "lupton" ? "" : "none";
}

// Clump List.
async function loadClumpList() {
    const filter = document.getElementById("clump-filter");
    let url = `${dsBase()}/clumps`;
    if (filter.value) url += `?component=${filter.value}`;

    const resp = await fetch(url);
    const data = await resp.json();
    state.clumps = data.clumps;
    renderClumpList();
}

function renderClumpList() {
    const container = document.getElementById("clump-list");
    let html = "";
    for (const c of state.clumps) {
        const isSelected = state.selectedClumps.has(c.clump_id);
        const clumpBadge = c.component == "disk" ? "disk" : "outside";
        html += `
            <div class="clump-item ${isSelected ? "selected" : ""}"
                 onclick="toggleClumpSelection(${c.clump_id})">
                <input type="checkbox" ${isSelected ? "checked" : ""}
                       onclick="event.stopPropagation(); toggleClumpSelection(${c.clump_id})">
                <span>Clump ${c.clump_id}</span>
                <span class="clump-badge ${clumpBadge}">${c.component}</span>
                <span style="color: var(--text-secondary); font-size: 10px; margin-left: auto;">
                    ${c.area_pix}px
                </span>
            </div>`;
    }
    container.innerHTML = html;
}

function updateClumpListUI() {
    const clumps = document.querySelectorAll(".clump-item");
    clumps.forEach((clump) => {
        const checkbox = clump.querySelector("input[type=checkbox]");
        const clumpId = Number.parseInt(clump.querySelector("span").textContent.replace("Clump ", ""));
        const isSelected = state.selectedClumps.has(clumpId);
        clump.classList.toggle("selected", isSelected);
        if (checkbox) checkbox.checked = isSelected;
    });
}

// Galaxy Viewer.
async function renderViewer() {
    const selectedStr = Array.from(state.selectedClumps).join(",");
    let url;

    if (state.viewMode === "rgb") {
        url = `${dsBase()}/viewer/${state.datacube}/rgb?r=${state.rgbR}&g=${state.rgbG}&b=${state.rgbB}&selected=${selectedStr}&method=${state.rgbMethod}&softening=${state.rgbQ}`;
    } else {
        url = `${dsBase()}/viewer/${state.datacube}/${state.channel}?selected=${selectedStr}&colorscale=${state.colorscale}&stretch=${state.stretch}`;
    }

    const resp = await fetch(url);
    const data = await resp.json();
    const fig = data.figure;

    fig.layout.dragmode = state.dragmode;

    if (!state.showBoundaries) {
        fig.data = fig.data.filter((t) => !(t.name?.startsWith("Clump ")));
    }

    if (!state.showCentroids) {
        fig.data.pop();
    }

    const viewer = document.getElementById("galaxy-viewer");
    await Plotly.react(viewer, fig.data, fig.layout, plotlyConfig);

    // Attach click handler
    viewer.removeAllListeners?.("plotly_click");
    viewer.on("plotly_click", onViewerClick);

    attachZoomOutLock(viewer);
}

// Custom wheel-zoom for the locked image plots.
//
// We replace Plotly's built-in scrollZoom (disabled in plotlyConfig) so we
// can clamp every new range to the layout's [minallowed, maxallowed] before
// calling Plotly.relayout. This eliminates the visible bounce that occurs
// when Plotly's default handler computes a range that overshoots the FOV
// and is then snapped back by minallowed/maxallowed.
//
// The zoom is also floored at min_span (5 pixels worth of axis units, set by
// the server in layout.meta.imageBounds) so the user cannot zoom past the
// image's pixel resolution.
function _readBounds(viewer, axisName) {
    const axis = viewer.layout?.[axisName];
    if (!axis?.range) return null;
    const {minallowed, maxallowed, range} = axis;
    if (minallowed === undefined || maxallowed === undefined) return null;
    const [r0, r1] = range;
    const meta = viewer.layout?.meta?.imageBounds ?? {};
    const minSpanKey = axisName === "xaxis" ? "x_min_span" : "y_min_span";
    return {
        lo: Math.min(r0, r1),
        hi: Math.max(r0, r1),
        min: minallowed,
        max: maxallowed,
        minSpan: meta[minSpanKey],
    };
}

function _clampRange(lo, hi, min, max, minSpan) {
    const fovSpan = max - min;
    let span = hi - lo;

    // Floor: if requested span is below minSpan, expand around the center
    // (capped by fovSpan so we never exceed the FOV).
    if (minSpan && span < minSpan) {
        const target = Math.min(minSpan, fovSpan);
        const center = (lo + hi) / 2;
        lo = center - target / 2;
        hi = center + target / 2;
        span = hi - lo;
    }

    // Ceiling: never exceed FOV.
    if (span >= fovSpan) {
        return [min, max];
    }
    if (lo < min) {
        hi += min - lo;
        lo = min;
    }
    if (hi > max) {
        lo -= hi - max;
        hi = max;
    }
    return [lo, hi];
}

function _zoomAxis(b, cursor, factor) {
    const newLo = cursor - (cursor - b.lo) * factor;
    const newHi = cursor + (b.hi - cursor) * factor;
    return _clampRange(newLo, newHi, b.min, b.max, b.minSpan);
}

function _cursorOnAxis(axis, pixel, fallback) {
    const v = axis?.p2d?.(pixel);
    return (typeof v === "number" && Number.isFinite(v)) ? v : fallback;
}

function _zoomOnWheel(e) {
    const div = e.currentTarget;
    const xa = _readBounds(div, "xaxis");
    const ya = _readBounds(div, "yaxis");
    if (!xa || !ya) return;

    e.preventDefault();
    e.stopPropagation();

    const factor = Math.exp(e.deltaY * 0.0015);

    const fullXa = div._fullLayout?.xaxis;
    const fullYa = div._fullLayout?.yaxis;
    const rect = div.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    const cx = _cursorOnAxis(fullXa, offsetX, (xa.lo + xa.hi) / 2);
    const cy = _cursorOnAxis(fullYa, offsetY, (ya.lo + ya.hi) / 2);

    const [xLo, xHi] = _zoomAxis(xa, cx, factor);
    const [yLo, yHi] = _zoomAxis(ya, cy, factor);

    Plotly.relayout(div, {
        "xaxis.range": [xLo, xHi],
        "yaxis.range": [yLo, yHi],
    });
}

// Re-clamp ranges produced by external paths (toolbar zoom-in, drag-rectangle,
// double-click). Plotly fires plotly_relayout *after* applying the range; if
// the new range is below min_span we relayout once more to grow back up to
// min_span. The __clamping flag prevents feedback loops.
function _relayoutClampGuard(div, eventData) {
    if (div.__clamping) return;

    const xRangeChanged = "xaxis.range" in eventData ||
        "xaxis.range[0]" in eventData || "xaxis.range[1]" in eventData;
    const yRangeChanged = "yaxis.range" in eventData ||
        "yaxis.range[0]" in eventData || "yaxis.range[1]" in eventData;
    if (!xRangeChanged && !yRangeChanged) return;

    const xa = _readBounds(div, "xaxis");
    const ya = _readBounds(div, "yaxis");
    if (!xa || !ya) return;

    const [xLo, xHi] = _clampRange(xa.lo, xa.hi, xa.min, xa.max, xa.minSpan);
    const [yLo, yHi] = _clampRange(ya.lo, ya.hi, ya.min, ya.max, ya.minSpan);

    const eps = 1e-9;
    const xChanged = Math.abs(xLo - xa.lo) > eps || Math.abs(xHi - xa.hi) > eps;
    const yChanged = Math.abs(yLo - ya.lo) > eps || Math.abs(yHi - ya.hi) > eps;
    if (!xChanged && !yChanged) return;

    div.__clamping = true;
    Plotly.relayout(div, {
        "xaxis.range": [xLo, xHi],
        "yaxis.range": [yLo, yHi],
    }).finally(() => {
        div.__clamping = false;
    });
}

function attachZoomOutLock(viewer) {
    if (viewer.__zoomOutLockAttached) return;
    viewer.addEventListener("wheel", _zoomOnWheel, {capture: true, passive: false});
    viewer.on("plotly_relayout", (ed) => _relayoutClampGuard(viewer, ed));
    // plotly_relayouting fires every frame during a drag (pan, drag-zoom).
    // For drag-zoom rectangles it carries xaxis.range and we clamp; for pan
    // Plotly translates the SVG via CSS transform and never emits range keys
    // until mouseup, so the custom pan handler below replaces Plotly's pan.
    viewer.on("plotly_relayouting", (ed) => _relayoutClampGuard(viewer, ed));

    // Custom pan implementation: takes over mouse drag when dragmode is 'pan',
    // updating xaxis/yaxis range every frame with the FOV clamp applied. This
    // prevents the visible off-FOV translation that Plotly's built-in pan
    // produces because it commits range changes only on mouseup.
    viewer.addEventListener("mousedown", (e) => _panMouseDown(viewer, e), {capture: true});
    viewer.__zoomOutLockAttached = true;
}

const _PAN_DRAG_THRESHOLD = 3; // pixels before mousedown is treated as a drag

const _panState = {
    active: false,
    moved: false,
    viewer: null,
    startX: 0,
    startY: 0,
    startXRange: [0, 0],
    startYRange: [0, 0],
    plotWidth: 1,
    plotHeight: 1,
    plotOffsetX: 0,
    plotOffsetY: 0,
};

function _panMouseDown(viewer, e) {
    if (state.dragmode !== "pan") return;
    if (e.button !== 0) return; // left button only

    const xa = _readBounds(viewer, "xaxis");
    const ya = _readBounds(viewer, "yaxis");
    if (!xa || !ya) return;

    const fullXa = viewer._fullLayout?.xaxis;
    const fullYa = viewer._fullLayout?.yaxis;
    const w = fullXa?._length;
    const h = fullYa?._length;
    if (!w || !h) return;

    // Bail if the click is outside the plot drawing area (modeBar, colorbar,
    // legend). Use the axis offsets/lengths to define the rect.
    const rect = viewer.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;
    const x0 = fullXa._offset;
    const y0 = fullYa._offset;
    if (px < x0 || px > x0 + w || py < y0 || py > y0 + h) return;

    // Always swallow the mousedown so Plotly's built-in pan does not also
    // run; we synthesize the click ourselves on mouseup if the user did not
    // actually drag.
    e.preventDefault();
    e.stopPropagation();

    _panState.active = true;
    _panState.moved = false;
    _panState.viewer = viewer;
    _panState.startX = e.clientX;
    _panState.startY = e.clientY;
    _panState.startXRange = [xa.lo, xa.hi];
    _panState.startYRange = [ya.lo, ya.hi];
    _panState.plotWidth = w;
    _panState.plotHeight = h;
    _panState.plotOffsetX = x0;
    _panState.plotOffsetY = y0;

    globalThis.addEventListener("mousemove", _panMouseMove, {capture: true});
    globalThis.addEventListener("mouseup", _panMouseUp, {capture: true});
}

function _panMouseMove(e) {
    if (!_panState.active) return;

    const viewer = _panState.viewer;
    const dxPix = e.clientX - _panState.startX;
    const dyPix = e.clientY - _panState.startY;

    if (!_panState.moved) {
        if (Math.abs(dxPix) + Math.abs(dyPix) < _PAN_DRAG_THRESHOLD) return;
        _panState.moved = true;
    }

    e.preventDefault();
    e.stopPropagation();

    const xSpan = _panState.startXRange[1] - _panState.startXRange[0];
    const ySpan = _panState.startYRange[1] - _panState.startYRange[0];
    // Pixel x grows right, data x grows right => drag right shifts view left.
    // Pixel y grows down, data y grows up   => drag down shifts view up.
    const dxData = -dxPix * xSpan / _panState.plotWidth;
    const dyData = +dyPix * ySpan / _panState.plotHeight;

    const xa = _readBounds(viewer, "xaxis");
    const ya = _readBounds(viewer, "yaxis");
    if (!xa || !ya) return;

    const newXLo = _panState.startXRange[0] + dxData;
    const newXHi = _panState.startXRange[1] + dxData;
    const newYLo = _panState.startYRange[0] + dyData;
    const newYHi = _panState.startYRange[1] + dyData;
    const [xLo, xHi] = _clampRange(newXLo, newXHi, xa.min, xa.max, xa.minSpan);
    const [yLo, yHi] = _clampRange(newYLo, newYHi, ya.min, ya.max, ya.minSpan);

    if (viewer.__clamping) return;
    viewer.__clamping = true;
    Plotly.relayout(viewer, {
        "xaxis.range": [xLo, xHi],
        "yaxis.range": [yLo, yHi],
    }).finally(() => {
        viewer.__clamping = false;
    });
}

function _nearestIndex(arr, v) {
    if (!arr || arr.length === 0) return 0;
    let best = 0;
    let bestD = Math.abs(arr[0] - v);
    for (let i = 1; i < arr.length; i++) {
        const d = Math.abs(arr[i] - v);
        if (d < bestD) {
            bestD = d;
            best = i;
        }
    }
    return best;
}

function _synthesizeClick(viewer, clientX, clientY) {
    const fullXa = viewer._fullLayout?.xaxis;
    const fullYa = viewer._fullLayout?.yaxis;
    if (!fullXa?.p2d || !fullYa?.p2d) return;

    const rect = viewer.getBoundingClientRect();
    const px = clientX - rect.left - _panState.plotOffsetX;
    const py = clientY - rect.top - _panState.plotOffsetY;

    let xData;
    let yData;
    try {
        xData = fullXa.p2d(px);
        yData = fullYa.p2d(py);
    } catch (_) {
        return;
    }
    if (!Number.isFinite(xData) || !Number.isFinite(yData)) return;

    // The first data trace is the heatmap; its x/y arrays carry the (arcsec
    // or pixel) axis values per cell. Nearest-neighbour gives the integer
    // pixel index regardless of the axis units.
    const heatmap = viewer.data?.[0];
    const xArr = heatmap?.x;
    const yArr = heatmap?.y;
    let xPix;
    let yPix;
    if (Array.isArray(xArr) && Array.isArray(yArr) && xArr.length && yArr.length) {
        xPix = _nearestIndex(xArr, xData);
        yPix = _nearestIndex(yArr, yData);
    } else {
        xPix = Math.round(xData);
        yPix = Math.round(yData);
    }

    handlePixelClick(xPix, yPix);
}

function _panMouseUp(e) {
    if (!_panState.active) return;
    const viewer = _panState.viewer;
    const moved = _panState.moved;
    _panState.active = false;
    _panState.viewer = null;
    globalThis.removeEventListener("mousemove", _panMouseMove, {capture: true});
    globalThis.removeEventListener("mouseup", _panMouseUp, {capture: true});

    if (!moved && viewer) {
        e.preventDefault();
        e.stopPropagation();
        _synthesizeClick(viewer, e.clientX, e.clientY);
    }
}

async function handlePixelClick(x, y) {
    // Check if pixel belongs to a clump.
    const resp = await fetch(`${dsBase()}/pixel/${x}/${y}/clump`);
    const data = await resp.json();

    if (data.clump_id === null) {
        showPropertiesMessage(`Pixel (${x}, ${y}) — no clump`);
    } else {
        toggleClumpSelection(data.clump_id);
    }
}

async function onViewerClick(eventData) {
    if (!eventData.points || eventData.points.length == 0) return;
    const point = eventData.points[0];
    // Heatmap pointIndex is [row, col] => [y_pix, x_pix]; axes may be arcsec.
    const [y, x] = point.pointIndex;
    await handlePixelClick(x, y);
}

// Clump selection.
async function toggleClumpSelection(clumpId) {
    if (state.selectedClumps.has(clumpId)) {
        state.selectedClumps.delete(clumpId);
    } else {
        state.selectedClumps.add(clumpId);
    }

    updateClumpListUI();
    renderViewer(); // viewer overlay update — fire-and-forget is fine

    const selected = Array.from(state.selectedClumps);
    try {
        if (selected.length === 0) {
            clearPanels();
        } else if (selected.length === 1) {
            await showClumpDetails(selected[0]);
        } else {
            showPropertiesMessage(`Selected ${selected.length} clumps: ${selected.join(", ")}`);
        }
    } catch (e) {
        console.error(e);
    }
}

async function showClumpDetails(clumpId) {
    const propsResp = await fetch(`${dsBase()}/clumps/${clumpId}`);
    const propsData = await propsResp.json();
    const props = propsData.properties;
    let html = '<table class="prop-table">';
    for (const [key, val] of Object.entries(props)) {
        html += `<tr><td>${key}</td><td>${val}</td></tr>`;
    }
    html += "</table>";
    document.getElementById("properties-content").innerHTML = html;
}

function showPropertiesMessage(msg) {
    document.getElementById("properties-content").innerHTML =
        `<p style="color: var(--accent); font-size: 12px;">${msg}</p>`;
}

function clearPanels() {
    document.getElementById("properties-content").innerHTML =
        '<p class="placeholder">Click on a clump to see its properties</p>';
}

// Start
document.addEventListener("DOMContentLoaded", init);
