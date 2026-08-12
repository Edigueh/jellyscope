// Click → pixel → clump resolution. Ported verbatim from app.js.
// Rect/lasso hit-testing (latent win #2) lives in ./selection (Plotly-free).
import { panPlotOffset } from "./zoomPan";

export { clumpsInSelection } from "./selection";
export type { ClumpCentroid } from "./selection";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyDiv = any;

function nearestIndex(arr: number[], v: number): number {
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

// Map a client-space press (that was a click, not a drag) to an integer pixel
// and hand it to onPixel. Uses the pan-state plot offsets captured at mousedown.
export function synthesizeClick(
  viewer: PlotlyDiv,
  clientX: number,
  clientY: number,
  onPixel: (x: number, y: number) => void,
): void {
  const fullXa = viewer._fullLayout?.xaxis;
  const fullYa = viewer._fullLayout?.yaxis;
  if (!fullXa?.p2d || !fullYa?.p2d) return;

  const offset = panPlotOffset();
  const rect = viewer.getBoundingClientRect();
  const px = clientX - rect.left - offset.x;
  const py = clientY - rect.top - offset.y;

  let xData: number;
  let yData: number;
  try {
    xData = fullXa.p2d(px);
    yData = fullYa.p2d(py);
  } catch {
    return;
  }
  if (!Number.isFinite(xData) || !Number.isFinite(yData)) return;

  // Trace 0 is the heatmap; its x/y arrays carry the (arcsec or pixel) axis
  // values per cell. Nearest-neighbour → integer pixel regardless of units.
  const heatmap = viewer.data?.[0];
  const xArr = heatmap?.x;
  const yArr = heatmap?.y;
  let xPix: number;
  let yPix: number;
  if (Array.isArray(xArr) && Array.isArray(yArr) && xArr.length && yArr.length) {
    xPix = nearestIndex(xArr, xData);
    yPix = nearestIndex(yArr, yData);
  } else {
    xPix = Math.round(xData);
    yPix = Math.round(yData);
  }
  onPixel(xPix, yPix);
}

// Plotly plotly_click handler → pixel. Heatmap pointIndex is [row, col] =
// [y_pix, x_pix]; axes may be arcsec.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function pixelFromClickEvent(eventData: any): { x: number; y: number } | null {
  if (!eventData.points || eventData.points.length === 0) return null;
  const point = eventData.points[0];
  const [y, x] = point.pointIndex;
  return { x, y };
}
