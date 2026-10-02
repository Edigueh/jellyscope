// Static-hosted variant: fetch pre-baked JSON files instead of hitting a
// FastAPI backend. Function signatures + return types mirror the original
// dynamic api so `controller.ts` and `mountViewer.ts` don't change.
//
// Base path is relative (`./data/...`) so Pages' `/<repo>/` prefix and any
// other subpath deployment work transparently.
import type {
  ClumpDetailResponse,
  ClumpSeparationsResponse,
  ClumpsListResponse,
  DatacubesResponse,
  FiltersResponse,
  PixelClumpResponse,
  RGBViewerResponse,
  ViewerResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    url: string,
  ) {
    super(`${status} for ${url}`);
    this.name = "ApiError";
  }
}

const BASE = "./data";

function dsPath(dataset: string): string {
  return `${BASE}/${encodeURIComponent(dataset)}`;
}

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new ApiError(resp.status, url);
  return (await resp.json()) as T;
}

// Per-dataset meta (datacubes, filters per cube, RGB presets). Loaded once
// then cached — every subsequent api.* call resolves against this.
export interface DatasetMeta {
  datacubes: string[];
  filters: Record<string, FiltersResponse["filters"]>;
  rgb_presets: Record<string, { r: number; g: number; b: number; labels: string[]; key: string }[]>;
  stretches: string[];
}

const metaCache = new Map<string, Promise<DatasetMeta>>();

export function getDatasetMeta(dataset: string): Promise<DatasetMeta> {
  const hit = metaCache.get(dataset);
  if (hit) return hit;
  const p = getJSON<DatasetMeta>(`${dsPath(dataset)}/meta.json`);
  metaCache.set(dataset, p);
  return p;
}

// Pixel-index grid: cached per-dataset int16 array (ny × nx clump IDs).
interface PixelIndex {
  ny: number;
  nx: number;
  data: Int16Array;
}
const pixelIndexCache = new Map<string, Promise<PixelIndex>>();

async function loadPixelIndex(dataset: string): Promise<PixelIndex> {
  const hit = pixelIndexCache.get(dataset);
  if (hit) return hit;
  const p = (async () => {
    const resp = await fetch(`${dsPath(dataset)}/pixel_index.bin.gz`);
    if (!resp.ok) throw new ApiError(resp.status, `${dataset} pixel_index`);
    // Pages serves .bin.gz raw; decompress client-side.
    const stream = resp.body!.pipeThrough(new DecompressionStream("gzip"));
    const buf = await new Response(stream).arrayBuffer();
    const header = new Int32Array(buf, 0, 2);
    const [ny, nx] = [header[0], header[1]];
    const data = new Int16Array(buf, 8, ny * nx);
    return { ny, nx, data };
  })();
  pixelIndexCache.set(dataset, p);
  return p;
}

function pickRgbKey(meta: DatasetMeta, datacube: string, r: number, g: number, b: number): string {
  const presets = meta.rgb_presets[datacube] ?? [];
  if (presets.length === 0) throw new ApiError(404, `no rgb presets for ${datacube}`);
  // Exact match first.
  const exact = presets.find((p) => p.r === r && p.g === g && p.b === b);
  if (exact) return exact.key;
  // Nearest by squared filter-index distance — snaps arbitrary state to a
  // baked triple so the UI stays functional even when the user drags.
  let best = presets[0];
  let bestDist = Infinity;
  for (const p of presets) {
    const d = (p.r - r) ** 2 + (p.g - g) ** 2 + (p.b - b) ** 2;
    if (d < bestDist) {
      bestDist = d;
      best = p;
    }
  }
  return best.key;
}

export const api = {
  datacubes: async (ds: string): Promise<DatacubesResponse> => {
    const meta = await getDatasetMeta(ds);
    return { datacubes: meta.datacubes };
  },

  filters: async (ds: string, datacube: string): Promise<FiltersResponse> => {
    const meta = await getDatasetMeta(ds);
    return { filters: meta.filters[datacube] ?? [] };
  },

  clumps: async (ds: string, component?: string): Promise<ClumpsListResponse> => {
    const list = await getJSON<ClumpsListResponse>(`${dsPath(ds)}/clumps.json`);
    if (!component) return list;
    return { clumps: list.clumps.filter((c) => c.component === component) };
  },

  clump: (ds: string, id: number): Promise<ClumpDetailResponse> =>
    getJSON<ClumpDetailResponse>(`${dsPath(ds)}/clump/${id}.json`),

  separations: (ds: string): Promise<ClumpSeparationsResponse> =>
    getJSON<ClumpSeparationsResponse>(`${dsPath(ds)}/separations.json`),

  pixelClump: async (ds: string, x: number, y: number): Promise<PixelClumpResponse> => {
    const grid = await loadPixelIndex(ds);
    if (x < 0 || x >= grid.nx || y < 0 || y >= grid.ny) {
      return { clump_id: null, ambiguous: false };
    }
    const v = grid.data[y * grid.nx + x];
    return { clump_id: v >= 0 ? v : null, ambiguous: v === -2 };
  },

  viewerSingle: async (
    ds: string,
    datacube: string,
    channel: number,
    params: { selected: string; colorscale: string; stretch: string },
  ): Promise<ViewerResponse> => {
    // Baked stretches only; anything else falls back to log.
    const meta = await getDatasetMeta(ds);
    const stretch = meta.stretches.includes(params.stretch) ? params.stretch : "log";
    return getJSON<ViewerResponse>(
      `${dsPath(ds)}/viewer/${encodeURIComponent(datacube)}/${stretch}/${channel}.json`,
    );
  },

  viewerRGB: async (
    ds: string,
    datacube: string,
    params: {
      r: number;
      g: number;
      b: number;
      selected: string;
      method: string;
      softening: number;
    },
  ): Promise<RGBViewerResponse> => {
    const meta = await getDatasetMeta(ds);
    const key = pickRgbKey(meta, datacube, params.r, params.g, params.b);
    return getJSON<RGBViewerResponse>(
      `${dsPath(ds)}/rgb/${encodeURIComponent(datacube)}/${key}.json`,
    );
  },
};
