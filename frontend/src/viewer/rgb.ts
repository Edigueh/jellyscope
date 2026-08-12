// RGB channel resolution + wavelength-locked anchor snapping.
// Ported verbatim from the original app.js (logic unchanged); wavelengths are
// now passed in rather than read from a module global.

const DEFAULT_RGB_FILTERS: Record<"r" | "g" | "b", string> = {
  r: "F200W",
  g: "F115W",
  b: "F090W",
};

// Fallback wavelength offsets (µm) when default filters lack a WAVELENGTHS entry
// on first load. Match F200W−F115W and F115W−F090W.
export const RGB_DELTA_RG_FALLBACK = 0.836;
export const RGB_DELTA_GB_FALLBACK = 0.253;

type Wavelengths = Record<string, number>;
export interface RgbTriplet {
  r: number;
  g: number;
  b: number;
}

// Lookup index of each named default; require presence in filterList AND a known
// wavelength. Returns -1 for unresolved slots.
function resolveNamedRgb(filterList: string[], wl: Wavelengths): RgbTriplet {
  const lookup = (key: "r" | "g" | "b"): number => {
    const i = filterList.indexOf(DEFAULT_RGB_FILTERS[key]);
    return i >= 0 && wl[DEFAULT_RGB_FILTERS[key]] != null ? i : -1;
  };
  return { r: lookup("r"), g: lookup("g"), b: lookup("b") };
}

// All filters with a known wavelength, sorted ascending by λ.
function knownWavelengths(filterList: string[], wl: Wavelengths): { i: number; wl: number }[] {
  const known: { i: number; wl: number }[] = [];
  filterList.forEach((name, i) => {
    const w = wl[name];
    if (w != null) known.push({ i, wl: w });
  });
  known.sort((a, b) => a.wl - b.wl);
  return known;
}

// argmin distance to target.
function nearestKnownToWl(
  known: { i: number; wl: number }[],
  targetWl: number,
): { i: number; wl: number } {
  return known.reduce((a, b) => (Math.abs(a.wl - targetWl) <= Math.abs(b.wl - targetWl) ? a : b));
}

// Position-only fallback when fewer than 3 filters carry a wavelength.
function positionFallback(result: RgbTriplet, filterList: string[]): RgbTriplet {
  return {
    r: result.r >= 0 ? result.r : Math.max(0, filterList.length - 1),
    g: result.g >= 0 ? result.g : Math.floor(filterList.length / 2),
    b: Math.max(result.b, 0),
  };
}

export function resolveRgbDefaults(filterList: string[], wl: Wavelengths): RgbTriplet {
  const result = resolveNamedRgb(filterList, wl);
  if (result.r >= 0 && result.g >= 0 && result.b >= 0) return result;

  const known = knownWavelengths(filterList, wl);
  if (known.length < 3) return positionFallback(result, filterList);

  const lo = known[0];
  const hi = known[known.length - 1];
  const midPick = nearestKnownToWl(known, (lo.wl + hi.wl) / 2);

  if (result.r < 0) result.r = hi.i;
  if (result.b < 0) result.b = lo.i;
  if (result.g < 0) result.g = midPick.i;
  return result;
}

// argmin over filterList of |λ − targetWl|; skips filters without a wavelength.
// Returns fallbackIndex if none qualify.
export function nearestFilterIndex(
  filterList: string[],
  wl: Wavelengths,
  targetWl: number,
  fallbackIndex: number,
): number {
  let best = -1;
  let bestDist = Infinity;
  filterList.forEach((name, i) => {
    const w = wl[name];
    if (w == null) return;
    const d = Math.abs(w - targetWl);
    if (d < bestDist) {
      best = i;
      bestDist = d;
    }
  });
  return best >= 0 ? best : fallbackIndex;
}

// Capture the locked wavelength offsets ΔRG = λ_R − λ_G and ΔGB = λ_G − λ_B from
// the current triplet. If either is non-positive/unresolvable (degenerate or
// unsorted default), fall back to BOTH constants — partial fallback would mix
// scales from different sources.
export function captureRgbDeltas(
  filterList: string[],
  wl: Wavelengths,
  rgb: RgbTriplet,
): { deltaRG: number; deltaGB: number } {
  const wlR = wl[filterList[rgb.r]];
  const wlG = wl[filterList[rgb.g]];
  const wlB = wl[filterList[rgb.b]];
  const dRG = wlR != null && wlG != null ? wlR - wlG : null;
  const dGB = wlG != null && wlB != null ? wlG - wlB : null;
  if (dRG != null && dGB != null && dRG > 0 && dGB > 0) {
    return { deltaRG: dRG, deltaGB: dGB };
  }
  return { deltaRG: RGB_DELTA_RG_FALLBACK, deltaGB: RGB_DELTA_GB_FALLBACK };
}

// Snap the two non-anchor slots to the filters nearest the locked-offset targets
// relative to the anchor's wavelength. Mutates and returns a new triplet.
export function snapRgbFromAnchor(
  anchor: "R" | "G" | "B",
  filterList: string[],
  wl: Wavelengths,
  rgb: RgbTriplet,
  deltaRG: number,
  deltaGB: number,
): RgbTriplet {
  const anchorIdx = anchor === "R" ? rgb.r : anchor === "G" ? rgb.g : rgb.b;
  const wlAnchor = wl[filterList[anchorIdx]];
  if (wlAnchor == null) return rgb; // anchor has no λ — nothing to snap to.

  const next = { ...rgb };
  if (anchor === "R") {
    next.g = nearestFilterIndex(filterList, wl, wlAnchor - deltaRG, rgb.g);
    next.b = nearestFilterIndex(filterList, wl, wlAnchor - deltaRG - deltaGB, rgb.b);
  } else if (anchor === "G") {
    next.r = nearestFilterIndex(filterList, wl, wlAnchor + deltaRG, rgb.r);
    next.b = nearestFilterIndex(filterList, wl, wlAnchor - deltaGB, rgb.b);
  } else {
    next.g = nearestFilterIndex(filterList, wl, wlAnchor + deltaGB, rgb.g);
    next.r = nearestFilterIndex(filterList, wl, wlAnchor + deltaGB + deltaRG, rgb.r);
  }
  return next;
}
