// Central app state shared between the (non-Preact) viewer science core and the
// Preact chrome. A tiny observable store rather than @preact/signals — the
// reactivity need is coarse (re-render panels on change), not fine-grained, so a
// dependency isn't worth it.
// ponytail: hand-rolled pub/sub, swap for @preact/signals only if fine-grained
// updates ever matter.
import { resolveRgbDefaults } from "./viewer/rgb";
import { readBootstrap } from "./bootstrap";

export type ViewMode = "single" | "rgb";
export type DragMode = "pan" | "select" | "lasso";

export interface AppState {
  dataset: string;
  datacube: string;
  channel: number;
  selectedClumps: Set<number>;
  colorscale: string;
  stretch: string;
  dragmode: DragMode;
  showCentroids: boolean;
  showBoundaries: boolean;
  viewMode: ViewMode;
  rgbR: number;
  rgbG: number;
  rgbB: number;
  // Wavelength offsets (µm) locked at datacube load; drive anchor snapping.
  rgbDeltaRG: number | null;
  rgbDeltaGB: number | null;
  rgbQ: number;
  rgbMethod: string;
  // Active filter list (names), refreshed when dataset/datacube changes.
  filters: string[];
  datacubes: string[];
  wavelengths: Record<string, number>;
  railCollapsed: boolean;
}

const boot = readBootstrap();
const initialRgb = resolveRgbDefaults(boot.filters, boot.wavelengths);

export const state: AppState = {
  dataset: boot.default_dataset,
  datacube: boot.default_datacube,
  channel: Math.min(7, Math.max(0, boot.filters.length - 1)),
  selectedClumps: new Set<number>(),
  colorscale: "Viridis",
  stretch: "lupton_asinh",
  dragmode: "pan",
  showCentroids: false,
  showBoundaries: true,
  viewMode: "single",
  rgbR: initialRgb.r,
  rgbG: initialRgb.g,
  rgbB: initialRgb.b,
  rgbDeltaRG: null,
  rgbDeltaGB: null,
  rgbQ: 8,
  rgbMethod: "percentile_asinh",
  filters: boot.filters.slice(),
  datacubes: boot.datacubes.slice(),
  wavelengths: boot.wavelengths,
  railCollapsed: false,
};

type Listener = () => void;
const listeners = new Set<Listener>();

/** Subscribe to any state change. Returns an unsubscribe fn. */
export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Notify all subscribers that state changed. Call after mutating `state`. */
export function emitChange(): void {
  for (const fn of listeners) fn();
}
