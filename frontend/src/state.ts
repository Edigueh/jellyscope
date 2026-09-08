// Central app state shared between the (non-Preact) viewer science core and the
// Preact chrome. A tiny observable store rather than @preact/signals — the
// reactivity need is coarse (re-render panels on change), not fine-grained, so a
// dependency isn't worth it.
// ponytail: hand-rolled pub/sub, swap for @preact/signals only if fine-grained
// updates ever matter.
import { readBootstrap } from "./bootstrap";
import { resolveRgbDefaults } from "./viewer/rgb";

export type ViewMode = "single" | "rgb";
export type DragMode = "pan" | "select" | "lasso";

export interface AppState {
  datasets: string[];
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

export const state: AppState = {
  datasets: [],
  dataset: "",
  datacube: "",
  channel: 0,
  selectedClumps: new Set<number>(),
  colorscale: "Viridis",
  stretch: "lupton_asinh",
  dragmode: "pan",
  showCentroids: false,
  showBoundaries: true,
  viewMode: "single",
  rgbR: 0,
  rgbG: 0,
  rgbB: 0,
  rgbDeltaRG: null,
  rgbDeltaGB: null,
  rgbQ: 8,
  rgbMethod: "percentile_asinh",
  filters: [],
  datacubes: [],
  wavelengths: {},
  railCollapsed: false,
};

// Populate `state` from the static manifest. main.tsx awaits this before
// mounting the Preact tree — components can then read state synchronously.
export async function initState(): Promise<void> {
  const boot = await readBootstrap();
  const initialRgb = resolveRgbDefaults(boot.filters, boot.wavelengths);
  state.datasets = boot.datasets;
  state.dataset = boot.default_dataset;
  state.datacube = boot.default_datacube;
  state.channel = Math.min(7, Math.max(0, boot.filters.length - 1));
  state.rgbR = initialRgb.r;
  state.rgbG = initialRgb.g;
  state.rgbB = initialRgb.b;
  state.filters = boot.filters.slice();
  state.datacubes = boot.datacubes.slice();
  state.wavelengths = boot.wavelengths;
}

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
