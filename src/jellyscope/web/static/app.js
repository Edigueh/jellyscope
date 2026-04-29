/**
 * Jellyscope — Frontend controller
 * Manages state, API calls, Plotly rendering, and user interactions.
 */
const state = {
    datacube: "nircam",
    channel: 7, // F200W default
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

// Initialization.

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
            Plotly.relayout(viewer, {dragmode: mode});
        });
    });

    document.getElementById("clump-filter").addEventListener("change", loadClumpList);
}

// Clump List.
async function loadClumpList() {
    const filter = document.getElementById("clump-filter");
    let url = "/api/clumps";
    let html = "";
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
}

async function onViewerClick(eventData) {
    if (!eventData.points || eventData.points.length == 0) return;
    const point = eventData.points[0];
    const x = Math.round(point.x);
    const y = Math.round(point.y);

    // Check if pixel belongs to a clump.
    const resp = await fetch(`/api/pixel/${x}/${y}/clump`);
    const data = await resp.json();

    if (data.clump_id !== null) {
        toggleClumpSelection(data.clump_id);
    }
}

async function onViewerSelected(eventData) {
    if (!eventData.points || eventData.points.length == 0) return;

    const pixels = eventData.points
        .filter((p) => p.curveNumber == 0) // Only heatmap points.
        .map((p) => [Math.round(p.x), Math.round(p.y)]);

    if(pixels.length === 0)  return;
}

// Clump selection.
function toggleClumpSelection(clumpId) {
    if(state.selectedClumps.has(clumpId)) {
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
    }
}

async function showClumpDetails(clumpId) {
    const propsResp = await fetch(`/api/clumps/${clumpId}`)

    const propsData = await propsResp.json();
    const props = propsData.properties;
    let html = '<table class="prop-table">';
    for (const [key, val] of Object.entries(props)) {
        html += `<tr><td>${key}</td><td>${val}</td></tr>`;
    }
    html += "</table>";
    document.getElementById("properties-content").innerHTML = html;
}

// Helpers
function clearPanels() {
    document.getElementById("properties-content").innerHTML =
        '<p class="placeholder">Click on a clump to see its properties</p>';
}

// Start
document.addEventListener("DOMContentLoaded", init);
