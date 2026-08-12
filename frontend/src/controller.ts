// Imperative actions bridging Preact chrome ↔ science core ↔ state. Components
// call these; they mutate `state`, drive the viewer, and emitChange() so the
// chrome re-renders. Mirrors the event handlers from the original app.js.
import { api, ApiError } from "./api";
import { emitChange, state } from "./state";
import type { AppState } from "./state";
import { renderViewer, resizeViewer, setDragmode } from "./viewer/mountViewer";
import {
  applyClumpSelectionColors,
  recolorClump,
  setBoundariesVisible,
  setCentroidsVisible,
} from "./viewer/overlays";
import { getViewerEl } from "./viewer/mountViewer";
import { captureRgbDeltas, resolveRgbDefaults, snapRgbFromAnchor } from "./viewer/rgb";
import type { ClumpDetailResponse, ClumpListItem, ClumpSeparationsResponse } from "./types";

// Chrome-visible data the components render (kept beside state; not part of the
// viewer contract).
export interface ChromeData {
  clumps: ClumpListItem[];
  clumpFilter: string;
  coordReadout: string;
  loading: boolean;
  // properties panel: single-clump detail, or null
  detail: ClumpDetailResponse | null;
  // multi-select compare: id → detail
  compare: Map<number, ClumpDetailResponse>;
  separations: ClumpSeparationsResponse | null;
  separationsError: string | null;
}

export const chrome: ChromeData = {
  clumps: [],
  clumpFilter: "",
  coordReadout: "",
  loading: false,
  detail: null,
  compare: new Map(),
  separations: null,
  separationsError: null,
};

async function withLoading(fn: () => Promise<void>): Promise<void> {
  chrome.loading = true;
  emitChange();
  try {
    await fn();
  } finally {
    chrome.loading = false;
    emitChange();
  }
}

// --- Source ---

export async function setDataset(dataset: string): Promise<void> {
  state.dataset = dataset;
  await withLoading(async () => {
    const { datacubes } = await api.datacubes(dataset);
    state.datacubes = datacubes;
    state.datacube = datacubes.includes(state.datacube) ? state.datacube : datacubes[0];

    const { filters } = await api.filters(dataset, state.datacube);
    state.filters = filters.map((f) => f.name);
    if (state.channel >= state.filters.length) state.channel = 0;

    rebuildRgb();
    state.selectedClumps.clear();
    clearDetail();
    await loadClumps();
    await renderViewer();
  });
  // datacube list changed — components re-read state.
  emitChange();
}

export async function setDatacube(datacube: string): Promise<void> {
  state.datacube = datacube;
  await withLoading(renderViewer);
}

// --- View mode + single-band controls ---

export async function setViewMode(mode: AppState["viewMode"]): Promise<void> {
  state.viewMode = mode;
  emitChange();
  await withLoading(renderViewer);
}

export async function setChannel(channel: number): Promise<void> {
  state.channel = channel;
  emitChange();
  await withLoading(renderViewer);
}

export async function setColorscale(cs: string): Promise<void> {
  state.colorscale = cs;
  await withLoading(renderViewer);
}

export async function setStretch(s: string): Promise<void> {
  state.stretch = s;
  await withLoading(renderViewer);
}

// --- RGB controls ---

function rebuildRgb(): void {
  const resolved = resolveRgbDefaults(state.filters, state.wavelengths);
  state.rgbR = resolved.r;
  state.rgbG = resolved.g;
  state.rgbB = resolved.b;
  const { deltaRG, deltaGB } = captureRgbDeltas(state.filters, state.wavelengths, resolved);
  state.rgbDeltaRG = deltaRG;
  state.rgbDeltaGB = deltaGB;
  const snapped = snapRgbFromAnchor("R", state.filters, state.wavelengths, resolved, deltaRG, deltaGB);
  state.rgbR = snapped.r;
  state.rgbG = snapped.g;
  state.rgbB = snapped.b;
}

// Capture deltas once for the initial triplet (called at startup).
export function initRgb(): void {
  const { deltaRG, deltaGB } = captureRgbDeltas(state.filters, state.wavelengths, {
    r: state.rgbR,
    g: state.rgbG,
    b: state.rgbB,
  });
  state.rgbDeltaRG = deltaRG;
  state.rgbDeltaGB = deltaGB;
  const snapped = snapRgbFromAnchor(
    "R",
    state.filters,
    state.wavelengths,
    { r: state.rgbR, g: state.rgbG, b: state.rgbB },
    deltaRG,
    deltaGB,
  );
  state.rgbR = snapped.r;
  state.rgbG = snapped.g;
  state.rgbB = snapped.b;
}

export async function setRgbChannel(anchor: "R" | "G" | "B", index: number): Promise<void> {
  if (anchor === "R") state.rgbR = index;
  else if (anchor === "G") state.rgbG = index;
  else state.rgbB = index;

  const snapped = snapRgbFromAnchor(
    anchor,
    state.filters,
    state.wavelengths,
    { r: state.rgbR, g: state.rgbG, b: state.rgbB },
    state.rgbDeltaRG ?? 0,
    state.rgbDeltaGB ?? 0,
  );
  state.rgbR = snapped.r;
  state.rgbG = snapped.g;
  state.rgbB = snapped.b;
  emitChange();
  await withLoading(renderViewer);
}

export async function setRgbMethod(method: string): Promise<void> {
  state.rgbMethod = method;
  emitChange();
  await withLoading(renderViewer);
}

let qTimer: ReturnType<typeof setTimeout> | undefined;
export function setRgbQ(q: number): void {
  state.rgbQ = q;
  emitChange();
  clearTimeout(qTimer);
  qTimer = setTimeout(() => void withLoading(renderViewer), 300);
}

// --- Tools + overlays ---

export function setDragMode(mode: AppState["dragmode"]): void {
  state.dragmode = mode;
  setDragmode(mode);
  emitChange();
}

export function toggleCentroids(): void {
  state.showCentroids = !state.showCentroids;
  const el = getViewerEl();
  if (el) setCentroidsVisible(el, state.showCentroids);
  emitChange();
}

export function toggleBoundaries(): void {
  state.showBoundaries = !state.showBoundaries;
  const el = getViewerEl();
  if (el) setBoundariesVisible(el, state.showBoundaries);
  emitChange();
}

// --- Clump list ---

export async function loadClumps(): Promise<void> {
  const { clumps } = await api.clumps(state.dataset, chrome.clumpFilter || undefined);
  chrome.clumps = clumps;
  emitChange();
}

export async function setClumpFilter(filter: string): Promise<void> {
  chrome.clumpFilter = filter;
  await loadClumps();
}

// --- Selection + panels ---

export async function handlePixel(x: number, y: number): Promise<void> {
  const { clump_id } = await api.pixelClump(state.dataset, x, y);
  if (clump_id === null) {
    chrome.detail = null;
    chrome.coordReadout = `pixel (${x}, ${y}) — no clump`;
    emitChange();
  } else {
    await toggleClump(clump_id);
  }
}

export async function toggleClump(clumpId: number): Promise<void> {
  if (state.selectedClumps.has(clumpId)) state.selectedClumps.delete(clumpId);
  else state.selectedClumps.add(clumpId);

  const el = getViewerEl();
  if (el) recolorClump(el, clumpId, state.selectedClumps.has(clumpId));
  await refreshSelectionPanels();
}

export async function selectClumps(ids: number[]): Promise<void> {
  for (const id of ids) state.selectedClumps.add(id);
  const el = getViewerEl();
  if (el) applyClumpSelectionColors(el, state.selectedClumps);
  await refreshSelectionPanels();
}

function clearDetail(): void {
  chrome.detail = null;
  chrome.compare.clear();
  chrome.separations = null;
  chrome.separationsError = null;
}

async function refreshSelectionPanels(): Promise<void> {
  const selected = Array.from(state.selectedClumps);
  clearDetail();

  if (selected.length === 1) {
    chrome.detail = await api.clump(state.dataset, selected[0]);
  } else if (selected.length >= 2) {
    // Multi-clump compare (latent win #3) + separations (latent win #1).
    const details = await Promise.all(selected.map((id) => api.clump(state.dataset, id)));
    selected.forEach((id, i) => chrome.compare.set(id, details[i]));
    await loadSeparations();
  }
  emitChange();
}

async function loadSeparations(): Promise<void> {
  try {
    chrome.separations = await api.separations(state.dataset);
    chrome.separationsError = null;
  } catch (e) {
    chrome.separations = null;
    chrome.separationsError =
      e instanceof ApiError && e.status === 422
        ? "Sky separations unavailable (no WCS for this dataset)."
        : "Could not load separations.";
  }
}

// --- Rail ---

export function toggleRail(): void {
  state.railCollapsed = !state.railCollapsed;
  emitChange();
  // Let the layout settle, then reflow Plotly to the new canvas width.
  requestAnimationFrame(() => resizeViewer());
}

export function setCoordReadout(text: string): void {
  chrome.coordReadout = text;
  emitChange();
}
