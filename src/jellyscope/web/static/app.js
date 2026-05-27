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

function defaultRgbIndex(filterName, fallback) {
    const idx = currentFilters.indexOf(filterName);
    return idx >= 0 ? idx : fallback;
}

// Filter state is recomputed when the dataset/datacube changes — keep
// the active filter list in module scope so the rest of the code can
// reference it without rereading the DOM. Initialized from the
// server-injected FILTERS constant, refreshed via the filters endpoint.
let currentFilters = FILTERS.slice();

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
    viewMode: "single", // "single" or "rgb"
    rgbR: defaultRgbIndex(DEFAULT_RGB_FILTERS.r, FILTERS.length - 1),
    rgbG: defaultRgbIndex(DEFAULT_RGB_FILTERS.g, Math.floor(FILTERS.length / 2)),
    rgbB: defaultRgbIndex(DEFAULT_RGB_FILTERS.b, 0),
    rgbQ: 8.0,
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
    state.rgbR = defaultRgbIndexFrom(currentFilters, DEFAULT_RGB_FILTERS.r, currentFilters.length - 1);
    state.rgbG = defaultRgbIndexFrom(currentFilters, DEFAULT_RGB_FILTERS.g, Math.floor(currentFilters.length / 2));
    state.rgbB = defaultRgbIndexFrom(currentFilters, DEFAULT_RGB_FILTERS.b, 0);
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
    updateRGBFilterOptions();
}

function defaultRgbIndexFrom(filterList, filterName, fallback) {
    const idx = filterList.indexOf(filterName);
    return idx >= 0 ? idx : fallback;
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
    updateRGBFilterOptions();
}

// Enforce λ_R > λ_G > λ_B by disabling invalid options.
// If current state.rgbG / rgbB violate the constraint, auto-pick the
// next-longest valid filter beneath the upstream one.
function updateRGBFilterOptions() {
    const wlOf = (i) => WAVELENGTHS[currentFilters[i]] ?? -Infinity;

    // G must have λ < λ_R; if violated, pick the longest filter still < λ_R.
    if (wlOf(state.rgbG) >= wlOf(state.rgbR)) {
        let best = -1;
        let bestWl = -Infinity;
        currentFilters.forEach((name, i) => {
            const wl = WAVELENGTHS[name] ?? -Infinity;
            if (wl < wlOf(state.rgbR) && wl > bestWl) {
                best = i;
                bestWl = wl;
            }
        });
        if (best >= 0) state.rgbG = best;
    }

    // B must have λ < λ_G; same fallback strategy.
    if (wlOf(state.rgbB) >= wlOf(state.rgbG)) {
        let best = -1;
        let bestWl = -Infinity;
        currentFilters.forEach((name, i) => {
            const wl = WAVELENGTHS[name] ?? -Infinity;
            if (wl < wlOf(state.rgbG) && wl > bestWl) {
                best = i;
                bestWl = wl;
            }
        });
        if (best >= 0) state.rgbB = best;
    }

    // Apply disabled flags + sync selected values to the (possibly updated) state.
    const limits = {
        "rgb-r": Infinity,
        "rgb-g": wlOf(state.rgbR),
        "rgb-b": wlOf(state.rgbG),
    };
    const current = {"rgb-r": state.rgbR, "rgb-g": state.rgbG, "rgb-b": state.rgbB};
    for (const id of Object.keys(limits)) {
        const sel = document.getElementById(id);
        if (!sel) continue;
        const max = limits[id];
        for (const opt of sel.options) {
            const wl = WAVELENGTHS[currentFilters[parseInt(opt.value)]] ?? -Infinity;
            opt.disabled = !(wl < max);
        }
        sel.value = String(current[id]);
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
        state.channel = parseInt(e.target.value);
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
        state.rgbR = parseInt(e.target.value);
        updateRGBFilterOptions();
        updateFilterLabel();
        renderViewer();
    });
    document.getElementById("rgb-g").addEventListener("change", (e) => {
        state.rgbG = parseInt(e.target.value);
        updateRGBFilterOptions();
        updateFilterLabel();
        renderViewer();
    });
    document.getElementById("rgb-b").addEventListener("change", (e) => {
        state.rgbB = parseInt(e.target.value);
        updateRGBFilterOptions();
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
        state.rgbQ = parseFloat(e.target.value);
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

    window.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const w = Math.max(260, Math.min(900, window.innerWidth - e.clientX));
        document.documentElement.style.setProperty("--sidebar-w", w + "px");
    });

    window.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        resizer.classList.remove("dragging");
        document.body.style.userSelect = "";
        const viewer = document.getElementById("galaxy-viewer");
        const spec = document.getElementById("spectrum-plot");
        if (viewer) Plotly.Plots.resize(viewer);
        if (spec && spec.data) Plotly.Plots.resize(spec);
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

    window.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const panelTop = clumpPanel.getBoundingClientRect().top;
        const totalH = rightPanels.getBoundingClientRect().height;
        // When SED is present, reserve ~280px for it (240px min-height + header).
        // When absent, the Clumps panel can grow to fill the column.
        const maxH = hasSed ? Math.max(60, totalH - 280) : Math.max(60, totalH - 20);
        const h = Math.max(60, Math.min(maxH, e.clientY - panelTop));
        document.documentElement.style.setProperty("--clump-h", h + "px");
    });

    window.addEventListener("mouseup", () => {
        if (!dragging) return;
        dragging = false;
        resizer.classList.remove("dragging");
        document.body.style.userSelect = "";
        const spec = document.getElementById("spectrum-plot");
        if (spec && spec.data) Plotly.Plots.resize(spec);
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
        const clumpId = parseInt(clump.querySelector("span").textContent.replace("Clump ", ""));
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

    if (data.clump_id !== null) {
        toggleClumpSelection(data.clump_id);
    } else {
        const myGen = ++spectrumGen;
        showPixelSpectrum(x, y, myGen);
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
