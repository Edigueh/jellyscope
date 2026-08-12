// Custom FOV-clamped wheel-zoom and pan for the locked image plots.
//
// Ported verbatim from the original app.js. Replaces Plotly's built-in
// scrollZoom/pan so every new range is clamped to [minallowed, maxallowed]
// before relayout — killing the visible bounce when Plotly overshoots the FOV,
// and flooring zoom at min_span (pixel resolution, from layout.meta.imageBounds).
//
// The div is a Plotly graph div; Plotly's runtime attaches _fullLayout, on(),
// removeAllListeners(), relayout via the Plotly module. Typed loosely.

import Plotly from "plotly.js-dist-min";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyDiv = any;

interface Bounds {
  lo: number;
  hi: number;
  min: number;
  max: number;
  minSpan: number | undefined;
}

const PAN_DRAG_THRESHOLD = 3; // pixels before mousedown is treated as a drag

function readBounds(viewer: PlotlyDiv, axisName: "xaxis" | "yaxis"): Bounds | null {
  const axis = viewer.layout?.[axisName];
  if (!axis?.range) return null;
  const { minallowed, maxallowed, range } = axis;
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

function clampRange(
  lo: number,
  hi: number,
  min: number,
  max: number,
  minSpan: number | undefined,
): [number, number] {
  const fovSpan = max - min;
  let span = hi - lo;

  // Floor: expand around center (capped by fovSpan) if below minSpan.
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

function zoomAxis(b: Bounds, cursor: number, factor: number): [number, number] {
  const newLo = cursor - (cursor - b.lo) * factor;
  const newHi = cursor + (b.hi - cursor) * factor;
  return clampRange(newLo, newHi, b.min, b.max, b.minSpan);
}

function cursorOnAxis(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  axis: any,
  pixel: number,
  fallback: number,
): number {
  const v = axis?.p2d?.(pixel);
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function zoomOnWheel(e: WheelEvent): void {
  const div = e.currentTarget as PlotlyDiv;
  const xa = readBounds(div, "xaxis");
  const ya = readBounds(div, "yaxis");
  if (!xa || !ya) return;

  e.preventDefault();
  e.stopPropagation();

  const factor = Math.exp(e.deltaY * 0.0015);

  const fullXa = div._fullLayout?.xaxis;
  const fullYa = div._fullLayout?.yaxis;
  const rect = div.getBoundingClientRect();
  const offsetX = e.clientX - rect.left;
  const offsetY = e.clientY - rect.top;
  const cx = cursorOnAxis(fullXa, offsetX, (xa.lo + xa.hi) / 2);
  const cy = cursorOnAxis(fullYa, offsetY, (ya.lo + ya.hi) / 2);

  const [xLo, xHi] = zoomAxis(xa, cx, factor);
  const [yLo, yHi] = zoomAxis(ya, cy, factor);
  Plotly.relayout(div, {
    "xaxis.range": [xLo, xHi],
    "yaxis.range": [yLo, yHi],
  });
}

// Re-clamp ranges produced by external paths (toolbar zoom-in, drag-rectangle,
// double-click). Clamps both axes so start-aspect is preserved.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function relayoutClampGuard(div: PlotlyDiv, eventData: Record<string, any>): void {
  if (div.__clamping) return;

  const xRangeChanged =
    "xaxis.range" in eventData || "xaxis.range[0]" in eventData || "xaxis.range[1]" in eventData;
  const yRangeChanged =
    "yaxis.range" in eventData || "yaxis.range[0]" in eventData || "yaxis.range[1]" in eventData;
  if (!xRangeChanged && !yRangeChanged) return;

  const xa = readBounds(div, "xaxis");
  const ya = readBounds(div, "yaxis");
  if (!xa || !ya) return;

  const [xLo, xHi] = clampRange(xa.lo, xa.hi, xa.min, xa.max, xa.minSpan);
  const [yLo, yHi] = clampRange(ya.lo, ya.hi, ya.min, ya.max, ya.minSpan);

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

// Clamp every layout.selections entry to image FOV. Plotly stores rect/lasso
// selections in data coords and never clips them.
function clampSelections(viewer: PlotlyDiv): void {
  const selections = viewer.layout?.selections;
  if (!selections?.length) return;
  const xa = readBounds(viewer, "xaxis");
  const ya = readBounds(viewer, "yaxis");
  if (!xa || !ya) return;

  const cx = (v: number) => Math.min(xa.max, Math.max(xa.min, v));
  const cy = (v: number) => Math.min(ya.max, Math.max(ya.min, v));

  let changed = false;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const next = selections.map((s: any) => {
    const c = { ...s };
    if (s.type === "rect") {
      const x0 = cx(s.x0);
      const x1 = cx(s.x1);
      const y0 = cy(s.y0);
      const y1 = cy(s.y1);
      if (x0 !== s.x0 || x1 !== s.x1 || y0 !== s.y0 || y1 !== s.y1) {
        changed = true;
        c.x0 = x0;
        c.x1 = x1;
        c.y0 = y0;
        c.y1 = y1;
      }
    } else if (s.path) {
      const clamped = s.path.replace(
        /([ML])\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)/g,
        (_: string, cmd: string, x: string, y: string) =>
          `${cmd}${cx(Number.parseFloat(x))},${cy(Number.parseFloat(y))}`,
      );
      if (clamped !== s.path) {
        changed = true;
        c.path = clamped;
      }
    }
    return c;
  });
  if (!changed) return;
  if (viewer.__clamping) return;

  viewer.__clamping = true;
  Plotly.relayout(viewer, { selections: next }).finally(() => {
    viewer.__clamping = false;
  });
}

interface PanState {
  active: boolean;
  moved: boolean;
  viewer: PlotlyDiv | null;
  startX: number;
  startY: number;
  startXRange: [number, number];
  startYRange: [number, number];
  plotWidth: number;
  plotHeight: number;
  plotOffsetX: number;
  plotOffsetY: number;
}

const panState: PanState = {
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

// Called on left-button mousedown when dragmode is 'pan'. onClickAtPixel is
// invoked (with integer pixel coords) if the press was a click, not a drag.
type PixelClickFn = (viewer: PlotlyDiv, clientX: number, clientY: number) => void;
let dragmodeGetter: () => string = () => "pan";
let synthesizeClick: PixelClickFn = () => {};

function panMouseDown(viewer: PlotlyDiv, e: MouseEvent): void {
  if (dragmodeGetter() !== "pan") return;
  if (e.button !== 0) return;

  const xa = readBounds(viewer, "xaxis");
  const ya = readBounds(viewer, "yaxis");
  if (!xa || !ya) return;

  const fullXa = viewer._fullLayout?.xaxis;
  const fullYa = viewer._fullLayout?.yaxis;
  const w = fullXa?._length;
  const h = fullYa?._length;
  if (!w || !h) return;

  const rect = viewer.getBoundingClientRect();
  const px = e.clientX - rect.left;
  const py = e.clientY - rect.top;
  const x0 = fullXa._offset;
  const y0 = fullYa._offset;
  if (px < x0 || px > x0 + w || py < y0 || py > y0 + h) return;

  e.preventDefault();
  e.stopPropagation();

  panState.active = true;
  panState.moved = false;
  panState.viewer = viewer;
  panState.startX = e.clientX;
  panState.startY = e.clientY;
  panState.startXRange = [xa.lo, xa.hi];
  panState.startYRange = [ya.lo, ya.hi];
  panState.plotWidth = w;
  panState.plotHeight = h;
  panState.plotOffsetX = x0;
  panState.plotOffsetY = y0;

  globalThis.addEventListener("mousemove", panMouseMove, { capture: true });
  globalThis.addEventListener("mouseup", panMouseUp, { capture: true });
}

function panMouseMove(e: MouseEvent): void {
  if (!panState.active) return;
  const viewer = panState.viewer;
  const dxPix = e.clientX - panState.startX;
  const dyPix = e.clientY - panState.startY;

  if (!panState.moved) {
    if (Math.abs(dxPix) + Math.abs(dyPix) < PAN_DRAG_THRESHOLD) return;
    panState.moved = true;
  }

  e.preventDefault();
  e.stopPropagation();

  const xSpan = panState.startXRange[1] - panState.startXRange[0];
  const ySpan = panState.startYRange[1] - panState.startYRange[0];
  const dxData = (-dxPix * xSpan) / panState.plotWidth;
  const dyData = (+dyPix * ySpan) / panState.plotHeight;

  const xa = readBounds(viewer, "xaxis");
  const ya = readBounds(viewer, "yaxis");
  if (!xa || !ya) return;

  const [xLo, xHi] = clampRange(
    panState.startXRange[0] + dxData,
    panState.startXRange[1] + dxData,
    xa.min,
    xa.max,
    xa.minSpan,
  );
  const [yLo, yHi] = clampRange(
    panState.startYRange[0] + dyData,
    panState.startYRange[1] + dyData,
    ya.min,
    ya.max,
    ya.minSpan,
  );

  if (viewer.__clamping) return;
  viewer.__clamping = true;
  Plotly.relayout(viewer, {
    "xaxis.range": [xLo, xHi],
    "yaxis.range": [yLo, yHi],
  }).finally(() => {
    viewer.__clamping = false;
  });
}

function panMouseUp(e: MouseEvent): void {
  if (!panState.active) return;
  const viewer = panState.viewer;
  const moved = panState.moved;
  panState.active = false;
  panState.viewer = null;
  globalThis.removeEventListener("mousemove", panMouseMove, { capture: true });
  globalThis.removeEventListener("mouseup", panMouseUp, { capture: true });

  if (!moved && viewer) {
    e.preventDefault();
    e.stopPropagation();
    synthesizeClick(viewer, e.clientX, e.clientY);
  }
}

/** Access to the live pan-state plot offsets, needed by click synthesis. */
export function panPlotOffset(): { x: number; y: number } {
  return { x: panState.plotOffsetX, y: panState.plotOffsetY };
}

/**
 * Attach the custom zoom/pan/selection-clamp handlers to a Plotly graph div.
 * Idempotent (guarded). `getDragmode` reads the current mode; `onPixelClick`
 * fires when a pan-mode press resolves to a click; `onSelect` fires on
 * rect/lasso selection (registered once, survives re-renders).
 */
export function attachZoomOutLock(
  viewer: PlotlyDiv,
  getDragmode: () => string,
  onPixelClick: PixelClickFn,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onSelect: (ed: any) => void,
): void {
  dragmodeGetter = getDragmode;
  synthesizeClick = onPixelClick;
  if (viewer.__zoomOutLockAttached) return;

  viewer.addEventListener("wheel", zoomOnWheel, { capture: true, passive: false });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer.on("plotly_relayout", (ed: Record<string, any>) => {
    relayoutClampGuard(viewer, ed);
    clampSelections(viewer);
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer.on("plotly_relayouting", (ed: Record<string, any>) => relayoutClampGuard(viewer, ed));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viewer.on("plotly_selected", (ed: any) => {
    clampSelections(viewer);
    onSelect(ed);
  });

  viewer.addEventListener("mousedown", (e: MouseEvent) => panMouseDown(viewer, e), {
    capture: true,
  });
  viewer.__zoomOutLockAttached = true;
}
