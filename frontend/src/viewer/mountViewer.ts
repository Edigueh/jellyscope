// Viewer orchestrator: fetch the figure for current state, Plotly.react it into
// #galaxy-viewer, wire hover/click/selection. Behavior ported from app.js
// renderViewer(); overlays + selection recolor are re-applied client-side after
// each fetch (no refetch on toggle).
import Plotly from "plotly.js-dist-min";
import { api } from "../api";
import { state } from "../state";
import { formatHoverReadout } from "./wcsHover";
import {
  applyClumpSelectionColors,
  setBoundariesVisible,
  setCentroidsVisible,
} from "./overlays";
import { attachZoomOutLock } from "./zoomPan";
import { clumpsInSelection, pixelFromClickEvent, synthesizeClick } from "./click";
import type { ClumpCentroid } from "./click";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyDiv = any;

const plotlyConfig = {
  responsive: true,
  displayModeBar: true,
  modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
  scrollZoom: false,
};

let viewerEl: PlotlyDiv | null = null;

// Callbacks into the app layer (set once at mount).
interface ViewerCallbacks {
  onPixel: (x: number, y: number) => void; // resolve pixel → clump, toggle
  onSelectClumps: (ids: number[]) => void; // rect/lasso enclosed clumps
  onHover: (readout: string) => void;
  clumpCentroids: () => ClumpCentroid[]; // current list, axis-space coords
}
let cb: ViewerCallbacks;

export function initViewer(el: HTMLElement, callbacks: ViewerCallbacks): void {
  viewerEl = el;
  cb = callbacks;
}

/** Fetch + render the figure for the current state. */
export async function renderViewer(): Promise<void> {
  if (!viewerEl) return;
  const selected = Array.from(state.selectedClumps).join(",");

  const data =
    state.viewMode === "rgb"
      ? await api.viewerRGB(state.dataset, state.datacube, {
          r: state.rgbR,
          g: state.rgbG,
          b: state.rgbB,
          selected,
          method: state.rgbMethod,
          softening: state.rgbQ,
        })
      : await api.viewerSingle(state.dataset, state.datacube, state.channel, {
          selected,
          colorscale: state.colorscale,
          stretch: state.stretch,
        });

  const fig = data.figure;
  fig.layout.dragmode = state.dragmode;

  await Plotly.react(viewerEl, fig.data, fig.layout, plotlyConfig);

  // Overlay visibility + selection colors are client-side; apply post-fetch.
  setBoundariesVisible(viewerEl, state.showBoundaries);
  setCentroidsVisible(viewerEl, state.showCentroids);
  applyClumpSelectionColors(viewerEl, state.selectedClumps);

  wireEvents(viewerEl);
  attachZoomOutLock(viewerEl, () => state.dragmode, onPixelPress, onRectLassoSelect);
}

function onRectLassoSelect(ed: unknown): void {
  if (!ed) return;
  const ids = clumpsInSelection(ed, cb.clumpCentroids());
  if (ids.length) cb.onSelectClumps(ids);
}

function onPixelPress(viewer: PlotlyDiv, clientX: number, clientY: number): void {
  synthesizeClick(viewer, clientX, clientY, cb.onPixel);
}

function wireEvents(viewer: PlotlyDiv): void {
  viewer.removeAllListeners?.("plotly_click");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer.on("plotly_click", (ed: any) => {
    const px = pixelFromClickEvent(ed);
    if (px) cb.onPixel(px.x, px.y);
  });

  viewer.removeAllListeners?.("plotly_hover");
  viewer.removeAllListeners?.("plotly_unhover");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer.on("plotly_hover", (ed: any) => cb.onHover(formatHoverReadout(viewer, ed)));
  viewer.on("plotly_unhover", () => cb.onHover(""));
}

/** Change dragmode without a refetch (mirrors the old mode-button behavior). */
export function setDragmode(mode: string): void {
  if (viewerEl) Plotly.relayout(viewerEl, { dragmode: mode });
}

/** Reflow after the rail resizes (mirrors the old resizer release). */
export function resizeViewer(): void {
  if (viewerEl) Plotly.Plots.resize(viewerEl);
}

export function getViewerEl(): PlotlyDiv | null {
  return viewerEl;
}
