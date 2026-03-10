/**
 * Jellyscope — Frontend controller
 * Manages state, API calls, Plotly rendering, and user interactions.
 */

const state = {
    datacube: "nircam",
    channel: 7,  // F200W default
    selectedClumps: new Set(),
    colorscale: "Viridis",
    dragmode: "pan",
    clumps: [],
};

const plotlyConfig = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    scrollZoom: true,
};

// ─── Initialization ────────────────────────────────────────────────

async function init() {
    await loadClumpList();
    await renderViewer();
    setupEventListeners();
}

function setupEventListeners() {
    document.getElementById("datacube-select").addEventListener("change", (e) => {
        state.datacube = e.target.value;
        renderViewer();
    });

    document.getElementById("filter-slider").addEventListener("input", (e) => {
        state.channel = parseInt(e.target.value);
        document.getElementById("filter-label").textContent = FILTERS[state.channel];
        renderViewer();
    });

    document.getElementById("colorscale-select").addEventListener("change", (e) => {
        state.colorscale = e.target.value;
        renderViewer();
    });

    document.querySelectorAll(".mode-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            const mode = btn.dataset.mode;
            state.dragmode = mode;
            const viewer = document.getElementById("galaxy-viewer");
            Plotly.relayout(viewer, { dragmode: mode });
        });
    });

    document.getElementById("clump-filter").addEventListener("change", loadClumpList);
}

// ─── Galaxy Viewer ─────────────────────────────────────────────────

async function renderViewer() {
    const selectedStr = Array.from(state.selectedClumps).join(",");
    const url = `/api/viewer/${state.datacube}/${state.channel}?selected=${selectedStr}&colorscale=${state.colorscale}`;
    const resp = await fetch(url);
    const data = await resp.json();
    const fig = data.figure;

    fig.layout.dragmode = state.dragmode;

    const viewer = document.getElementById("galaxy-viewer");
    await Plotly.react(viewer, fig.data, fig.layout, plotlyConfig);

    // Attach click handler
    viewer.removeAllListeners?.("plotly_click");
    viewer.on("plotly_click", onViewerClick);
    viewer.on("plotly_selected", onViewerSelected);
}

async function onViewerClick(eventData) {
    if (!eventData.points || eventData.points.length === 0) return;
    const point = eventData.points[0];
    const x = Math.round(point.x);
    const y = Math.round(point.y);

    // Check if pixel belongs to a clump
    const resp = await fetch(`/api/pixel/${x}/${y}/clump`);
    const data = await resp.json();

    if (data.clump_id !== null) {
        toggleClumpSelection(data.clump_id);
    } else {
        // Show pixel spectrum
        showPixelSpectrum(x, y);
    }
}

async function onViewerSelected(eventData) {
    if (!eventData || !eventData.points || eventData.points.length === 0) return;

    const pixels = eventData.points
        .filter((p) => p.curveNumber === 0)  // Only heatmap points
        .map((p) => [Math.round(p.x), Math.round(p.y)]);

    if (pixels.length === 0) return;

    const resp = await fetch(`/api/region/spectrum/${state.datacube}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pixels }),
    });
    const data = await resp.json();

    const specPlot = document.getElementById("spectrum-plot");
    Plotly.react(specPlot, data.figure.data, data.figure.layout, plotlyConfig);

    showPropertiesMessage(`Selected region: ${data.spectrum.n_pixels} pixels`);
}

// ─── Clump Selection ───────────────────────────────────────────────

function toggleClumpSelection(clumpId) {
    if (state.selectedClumps.has(clumpId)) {
        state.selectedClumps.delete(clumpId);
    } else {
        state.selectedClumps.add(clumpId);
    }
    updateClumpListUI();
    renderViewer();

    const selected = Array.from(state.selectedClumps);
    if (selected.length === 0) {
        clearPanels();
    } else if (selected.length === 1) {
        showClumpDetails(selected[0]);
    } else {
        showMultiClumpComparison(selected);
    }
}

async function showClumpDetails(clumpId) {
    // Fetch properties and spectrum in parallel
    const [propsResp, specResp] = await Promise.all([
        fetch(`/api/clumps/${clumpId}`),
        fetch(`/api/clumps/${clumpId}/spectrum/${state.datacube}`),
    ]);
    const propsData = await propsResp.json();
    const specData = await specResp.json();

    // Update properties panel
    const props = propsData.properties;
    let html = '<table class="prop-table">';
    for (const [key, value] of Object.entries(props)) {
        html += `<tr><td>${key}</td><td>${value}</td></tr>`;
    }
    html += "</table>";
    document.getElementById("properties-content").innerHTML = html;

    // Update spectrum plot
    const specPlot = document.getElementById("spectrum-plot");
    Plotly.react(specPlot, specData.figure.data, specData.figure.layout, plotlyConfig);
}

async function showMultiClumpComparison(clumpIds) {
    const resp = await fetch(`/api/compare/spectrum/${state.datacube}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clump_ids: clumpIds }),
    });
    const data = await resp.json();

    const specPlot = document.getElementById("spectrum-plot");
    Plotly.react(specPlot, data.figure.data, data.figure.layout, plotlyConfig);

    showPropertiesMessage(`Comparing ${clumpIds.length} clumps: ${clumpIds.join(", ")}`);
}

async function showPixelSpectrum(x, y) {
    const resp = await fetch(`/api/pixel/${x}/${y}/spectrum/${state.datacube}`);
    const data = await resp.json();

    const specPlot = document.getElementById("spectrum-plot");
    Plotly.react(specPlot, data.figure.data, data.figure.layout, plotlyConfig);

    showPropertiesMessage(`Pixel (${x}, ${y}) — no clump`);
}

// ─── Clump List ────────────────────────────────────────────────────

async function loadClumpList() {
    const filter = document.getElementById("clump-filter").value;
    let url = "/api/clumps";
    if (filter) url += `?component=${filter}`;

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
        const badgeClass = c.component === "disk" ? "disk" : "outside";
        html += `
            <div class="clump-item ${isSelected ? "selected" : ""}"
                 onclick="toggleClumpSelection(${c.clump_id})">
                <input type="checkbox" ${isSelected ? "checked" : ""}
                       onclick="event.stopPropagation(); toggleClumpSelection(${c.clump_id})">
                <span>Clump ${c.clump_id}</span>
                <span class="clump-badge ${badgeClass}">${c.component}</span>
                <span style="color: var(--text-secondary); font-size: 10px; margin-left: auto;">
                    ${c.area_pix}px
                </span>
            </div>`;
    }
    container.innerHTML = html;
}

function updateClumpListUI() {
    const items = document.querySelectorAll(".clump-item");
    items.forEach((item) => {
        const checkbox = item.querySelector("input[type=checkbox]");
        const clumpId = parseInt(item.querySelector("span").textContent.replace("Clump ", ""));
        const isSelected = state.selectedClumps.has(clumpId);
        item.classList.toggle("selected", isSelected);
        if (checkbox) checkbox.checked = isSelected;
    });
}

// ─── Helpers ───────────────────────────────────────────────────────

function showPropertiesMessage(msg) {
    document.getElementById("properties-content").innerHTML =
        `<p style="color: var(--accent); font-size: 12px;">${msg}</p>`;
}

function clearPanels() {
    document.getElementById("properties-content").innerHTML =
        '<p class="placeholder">Click on a clump to see its properties</p>';
    Plotly.purge(document.getElementById("spectrum-plot"));
}

// ─── Start ─────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", init);
