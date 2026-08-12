// RA/Dec hover readout, reconstructed client-side from the compact affine WCS in
// layout.meta.wcs. Plot axes are arcsec-from-center (celestial) → pixel →
// RA/Dec. Ported verbatim from app.js. Returns the readout string, or "" when
// the dataset has no celestial WCS.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyDiv = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HoverEvent = any;

export function formatHoverReadout(viewer: PlotlyDiv, eventData: HoverEvent): string {
  const pt = eventData.points?.[0];
  const w = viewer.layout?.meta?.wcs;
  if (!pt || !w) return "";
  // Axis coords (arcsec offset from center) → 0-based pixel.
  const xPix = w.cx + pt.x / w.arcsec_per_pix;
  const yPix = w.cy + pt.y / w.arcsec_per_pix;
  // Linear pixel → RA/Dec (rotation-free WCS; RA scaled by cos(dec0)).
  const ra = w.crval[0] + (w.scale[0] * (xPix - w.crpix[0])) / w.cos_dec;
  const dec = w.crval[1] + w.scale[1] * (yPix - w.crpix[1]);
  return `pix (${Math.round(xPix)}, ${Math.round(yPix)})  ·  RA ${ra.toFixed(6)}°  Dec ${dec.toFixed(6)}°`;
}
