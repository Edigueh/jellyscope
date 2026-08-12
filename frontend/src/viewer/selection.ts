// Pure geometry for rect/lasso → clump hit-testing (latent win #2). No Plotly
// dependency, so it's unit-testable in plain Node.

export interface ClumpCentroid {
  clump_id: number;
  // axis-space coords matching the heatmap x/y arrays (arcsec or pixel)
  x: number;
  y: number;
}

// Resolve the clumps enclosed by a Plotly rect/lasso selection event.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function clumpsInSelection(eventData: any, centroids: ClumpCentroid[]): number[] {
  const ranges = eventData?.range;
  const lasso = eventData?.lassoPoints;
  if (ranges?.x && ranges?.y) {
    const [x0, x1] = [Math.min(...ranges.x), Math.max(...ranges.x)];
    const [y0, y1] = [Math.min(...ranges.y), Math.max(...ranges.y)];
    return centroids
      .filter((c) => c.x >= x0 && c.x <= x1 && c.y >= y0 && c.y <= y1)
      .map((c) => c.clump_id);
  }
  if (lasso?.x && lasso?.y) {
    return centroids.filter((c) => pointInPolygon(c.x, c.y, lasso.x, lasso.y)).map((c) => c.clump_id);
  }
  return [];
}

// Standard ray-casting point-in-polygon.
function pointInPolygon(x: number, y: number, xs: number[], ys: number[]): boolean {
  let inside = false;
  for (let i = 0, j = xs.length - 1; i < xs.length; j = i++) {
    const xi = xs[i];
    const yi = ys[i];
    const xj = xs[j];
    const yj = ys[j];
    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}
