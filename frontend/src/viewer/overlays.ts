// Clump boundary/centroid visibility + selection recolor. Ported verbatim from
// app.js. Operates on already-fetched Plotly traces (no refetch).
import Plotly from "plotly.js-dist-min";
import {
  CLUMP_COLOR,
  CLUMP_SELECTED_COLOR,
  CLUMP_WIDTH,
  CLUMP_SELECTED_WIDTH,
} from "../theme";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyDiv = any;

// Trace indices whose name starts with "Clump " (the boundary outlines).
function boundaryTraceIndices(viewer: PlotlyDiv): number[] {
  return (viewer.data || [])
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .map((t: any, i: number) => (t.name?.startsWith("Clump ") ? i : -1))
    .filter((i: number) => i >= 0);
}

function clumpLineStyle(selected: boolean): { color: string; width: number } {
  return {
    color: selected ? CLUMP_SELECTED_COLOR : CLUMP_COLOR,
    width: selected ? CLUMP_SELECTED_WIDTH : CLUMP_WIDTH,
  };
}

export function setBoundariesVisible(viewer: PlotlyDiv, show: boolean): void {
  const idx = boundaryTraceIndices(viewer);
  if (idx.length) Plotly.restyle(viewer, { visible: show }, idx);
}

export function setCentroidsVisible(viewer: PlotlyDiv, show: boolean): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const i = (viewer.data || []).findIndex((t: any) => t.name === "Centroids");
  if (i >= 0) Plotly.restyle(viewer, { visible: show }, [i]);
}

// Recolor every boundary trace to match the selection set, in one restyle.
export function applyClumpSelectionColors(viewer: PlotlyDiv, selected: Set<number>): void {
  const idx = boundaryTraceIndices(viewer);
  if (!idx.length) return;
  const styles = idx.map((i) => {
    const id = Number.parseInt(viewer.data[i].name.replace("Clump ", ""));
    return clumpLineStyle(selected.has(id));
  });
  Plotly.restyle(
    viewer,
    {
      "line.color": styles.map((s) => s.color),
      "line.width": styles.map((s) => s.width),
    },
    idx,
  );
}

// Recolor a single clump's boundary to its current selection state. No refetch.
export function recolorClump(viewer: PlotlyDiv, clumpId: number, selected: boolean): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const i = (viewer.data || []).findIndex((t: any) => t.name === `Clump ${clumpId}`);
  if (i < 0) return; // no boundary trace (e.g. boundaries not drawn)
  const s = clumpLineStyle(selected);
  Plotly.restyle(viewer, { "line.color": s.color, "line.width": s.width }, [i]);
}
