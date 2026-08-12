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
  displayModeBar: false, // custom wheel-zoom + drag-pan + dbl-click reset replace it
  scrollZoom: false,
};

// Fixed figure margins (mirror _viz_helpers.py build_dark_axis_layout).
const MARGIN = { l: 48, r: 12, t: 12, b: 44 };

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

  // Size the plot box to the data aspect so pixels are square (letterboxed),
  // then reflow. Done via container sizing rather than a Plotly scaleanchor
  // lock, which fights the custom range-owning zoom/pan.
  fitPlotAspect();

  // Overlay visibility + selection colors are client-side; apply post-fetch.
  setBoundariesVisible(viewerEl, state.showBoundaries);
  setCentroidsVisible(viewerEl, state.showCentroids);
  applyClumpSelectionColors(viewerEl, state.selectedClumps);

  wireEvents(viewerEl);
  attachZoomOutLock(viewerEl, () => state.dragmode, onPixelPress, onRectLassoSelect);
}

// Size #galaxy-viewer so its *plot area* (element minus fixed margins) matches
// the data aspect ratio, and center it in its parent (the parent letterboxes
// with the canvas bg). No-op until meta.imageBounds ranges are present.
function fitPlotAspect(): void {
  if (!viewerEl) return;
  const b = viewerEl.layout?.meta?.imageBounds;
  if (!b?.x_range || !b?.y_range) return;

  const parent = viewerEl.parentElement as HTMLElement | null;
  if (!parent) return;
  const availW = parent.clientWidth;
  const availH = parent.clientHeight;
  if (availW <= 0 || availH <= 0) return;

  const dataW = b.x_range[1] - b.x_range[0];
  const dataH = b.y_range[1] - b.y_range[0];
  if (dataW <= 0 || dataH <= 0) return;
  const dataAspect = dataW / dataH; // plot-area width/height target

  const mx = MARGIN.l + MARGIN.r;
  const my = MARGIN.t + MARGIN.b;

  // Largest element (elW×elH ≤ avail) whose plot area (elW−mx)×(elH−my) has
  // ratio == dataAspect. Try width-limited first, fall back to height-limited.
  let elW = availW;
  let plotW = elW - mx;
  let plotH = plotW / dataAspect;
  let elH = plotH + my;
  if (elH > availH) {
    elH = availH;
    plotH = elH - my;
    plotW = plotH * dataAspect;
    elW = plotW + mx;
  }

  viewerEl.style.width = `${Math.max(0, Math.round(elW))}px`;
  viewerEl.style.height = `${Math.max(0, Math.round(elH))}px`;
  Plotly.Plots.resize(viewerEl);
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

/** Reflow after the rail resizes: re-fit the aspect box, then resize Plotly. */
export function resizeViewer(): void {
  fitPlotAspect();
}

export function getViewerEl(): PlotlyDiv | null {
  return viewerEl;
}
