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
    scrollZoom: true,
};

// Generation token: every time the selection changes, we bump this and
// pass the snapshot into spectrum-rendering helpers. If a stale async
// callback resolves after a newer selection, it bails out instead of
// clobbering the fresh render.
let spectrumGen = 0;

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
    setupClumpSedResizer();
}

// Draggable handle between viewer and right panels. Updates the --sidebar-w
// CSS var; clamps within sane bounds; nudges Plotly to reflow on release so
// the heatmap and SED both pick up the new column widths.
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
        const spec = document.getElementById("spectrum-plot");
        if (viewer) Plotly.Plots.resize(viewer);
        if (spec?.data) Plotly.Plots.resize(spec);
    });
}

// Vertical resizer between Clumps and SED panels. Updates --clump-h on the
// document root; clamps to sane bounds; nudges Plotly to reflow on release.
function setupClumpSedResizer() {
    const resizer = document.getElementById("clump-sed-resizer");
    if (!resizer) return;
    const rightPanels = document.getElementById("right-panels");
    const clumpPanel = document.getElementById("clump-list-panel");
    if (!rightPanels || !clumpPanel) return;
    const hasSed = !!document.getElementById("spectrum-panel");
    let dragging = false;

    resizer.addEventListener("mousedown", (e) => {
        dragging = true;
        resizer.classList.add("dragging");
        document.body.style.userSelect = "none";
        e.preventDefault();
    });

    globalThis.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const panelTop = clumpPanel.getBoundingClientRect().top;
        const totalH = rightPanels.getBoundingClientRect().height;
        // When SED is present, reserve ~280px for it (240px min-height + header).
        // When absent, the Clumps panel can grow to fill the column.
        const maxH = hasSed ? Math.max(60, totalH - 280) : Math.max(60, totalH - 20);
        const h = Math.max(60, Math.min(maxH, e.clientY - panelTop));
        document.documentElement.style.setProperty("--clump-h", h + "px");
    });

    globalThis.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        resizer.classList.remove("dragging");
        document.body.style.userSelect = "";
        const spec = document.getElementById("spectrum-plot");
        if (spec?.data) Plotly.Plots.resize(spec);
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
    viewer.removeAllListeners?.("plotly_selected");
    viewer.on("plotly_selected", onViewerSelected);
}

async function onViewerClick(eventData) {
    if (!eventData.points || eventData.points.length == 0) return;
    const point = eventData.points[0];
    const x = Math.round(point.x);
    const y = Math.round(point.y);

    // Check if pixel belongs to a clump.
    const resp = await fetch(`${dsBase()}/pixel/${x}/${y}/clump`);
    const data = await resp.json();

    if (data.clump_id === null) {
        const myGen = ++spectrumGen;
        showPixelSpectrum(x, y, myGen);
    } else {
        toggleClumpSelection(data.clump_id);
    }
}

async function onViewerSelected(eventData) {
    if (!eventData.points || eventData.points.length == 0) return;

    const pixels = eventData.points
        .filter((p) => p.curveNumber == 0) // Only heatmap points.
        .map((p) => [Math.round(p.x), Math.round(p.y)]);

    if (pixels.length === 0) return;

    const myGen = ++spectrumGen;
    const resp = await fetch(`${dsBase()}/region/spectrum/${state.datacube}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({pixels}),
    });
    if (myGen !== spectrumGen) return;
    const data = await resp.json();

    await renderSpectrum(data.figure, myGen);

    showPropertiesMessage(`Selected region: ${data.spectrum.n_pixels} pixels`);
}

// Clump selection.
async function toggleClumpSelection(clumpId) {
    if (state.selectedClumps.has(clumpId)) {
        state.selectedClumps.delete(clumpId);
    } else {
        state.selectedClumps.add(clumpId);
    }

    updateClumpListUI();
    const myGen = ++spectrumGen;
    renderViewer(); // viewer overlay update — fire-and-forget is fine

    const selected = Array.from(state.selectedClumps);
    try {
        if (selected.length === 0) {
            clearPanels();
        } else if (selected.length === 1) {
            await showClumpDetails(selected[0], myGen);
        } else {
            await showMultiClumpComparison(selected, myGen);
        }
    } catch (e) {
        if (myGen === spectrumGen) console.error(e);
    }
}

// Render the SED figure into the spectrum panel. We always do react+resize
// so the plot fills the flex container even when its trace count changes
// between calls (1 clump → N clumps could otherwise leave Plotly with a
// stale layout width from the previous render). If a gen token is supplied
// and it's stale, bail without touching the DOM — a newer render is in flight.
async function renderSpectrum(figure, gen) {
    if (gen !== undefined && gen !== spectrumGen) return;
    const plot = document.getElementById("spectrum-plot");
    await Plotly.react(plot, figure.data, figure.layout, plotlyConfig);
    Plotly.Plots.resize(plot);
}

async function showClumpDetails(clumpId, gen) {
    const [propsResp, specResp] = await Promise.all([
        fetch(`${dsBase()}/clumps/${clumpId}`),
        fetch(`${dsBase()}/clumps/${clumpId}/spectrum/${state.datacube}`),
    ]);

    if (gen !== undefined && gen !== spectrumGen) return;

    const propsData = await propsResp.json();
    const props = propsData.properties;
    let html = '<table class="prop-table">';
    for (const [key, val] of Object.entries(props)) {
        html += `<tr><td>${key}</td><td>${val}</td></tr>`;
    }
    html += "</table>";
    document.getElementById("properties-content").innerHTML = html;

    const specData = await specResp.json();
    await renderSpectrum(specData.figure, gen);
}

async function showMultiClumpComparison(clumpIds, gen) {
    const resp = await fetch(`${dsBase()}/compare/spectrum/${state.datacube}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({clump_ids: clumpIds}),
    });
    if (!resp.ok) {
        console.error("compare/spectrum failed:", resp.status, await resp.text());
        return;
    }
    if (gen !== undefined && gen !== spectrumGen) return;
    const data = await resp.json();
    await renderSpectrum(data.figure, gen);
    showPropertiesMessage(`Comparing ${clumpIds.length} clumps: ${clumpIds.join(", ")}`);
}

async function showPixelSpectrum(x, y, gen) {
    const resp = await fetch(`${dsBase()}/pixel/${x}/${y}/spectrum/${state.datacube}`);
    if (gen !== undefined && gen !== spectrumGen) return;
    const data = await resp.json();
    await renderSpectrum(data.figure, gen);
    showPropertiesMessage(`Pixel (${x}, ${y}) — no clump`);
}

function showPropertiesMessage(msg) {
    document.getElementById("properties-content").innerHTML =
        `<p style="color: var(--accent); font-size: 12px;">${msg}</p>`;
}

// Helpers. Purge (not react with empty data) so Plotly drops its internal
// layout cache — otherwise the next render reuses stale dimensions and can
// land as a zero-height plot.
function clearPanels() {
    document.getElementById("properties-content").innerHTML =
        '<p class="placeholder">Click on a clump to see its properties</p>';
    Plotly.purge(document.getElementById("spectrum-plot"));
}

// Start
document.addEventListener("DOMContentLoaded", init);
