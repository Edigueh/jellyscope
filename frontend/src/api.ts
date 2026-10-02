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
import { composeRgb, rgbToPngDataUrl } from "./viewer/rgbComposite";

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

interface ChannelCube {
  nChannels: number;
  ny: number;
  nx: number;
  data: Float64Array;
}

const channelCubeCache = new Map<string, Promise<ChannelCube>>();
const rgbTemplateCache = new Map<string, Promise<RGBViewerResponse>>();

async function loadChannelCube(dataset: string, datacube: string): Promise<ChannelCube> {
  const key = `${dataset}/${datacube}`;
  const hit = channelCubeCache.get(key);
  if (hit) return hit;
  const p = (async () => {
    const url = `${dsPath(dataset)}/channels/${encodeURIComponent(datacube)}.bin.gz`;
    const resp = await fetch(url);
    if (!resp.ok || !resp.body) throw new ApiError(resp.status, url);
    const stream = resp.body.pipeThrough(new DecompressionStream("gzip"));
    const buf = await new Response(stream).arrayBuffer();
    const header = new Int32Array(buf, 0, 4);
    const [version, nChannels, ny, nx] = header;
    if (version !== 1 || nChannels <= 0 || ny <= 0 || nx <= 0) {
      throw new ApiError(500, `${url} header`);
    }
    const count = nChannels * ny * nx;
    if (buf.byteLength !== 16 + count * Float64Array.BYTES_PER_ELEMENT) {
      throw new ApiError(500, `${url} size`);
    }
    return { nChannels, ny, nx, data: new Float64Array(buf, 16, count) };
  })();
  channelCubeCache.set(key, p);
  return p;
}

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

function loadRgbTemplate(meta: DatasetMeta, dataset: string, datacube: string): Promise<RGBViewerResponse> {
  const key = `${dataset}/${datacube}`;
  const hit = rgbTemplateCache.get(key);
  if (hit) return hit;
  const preset = meta.rgb_presets[datacube]?.[0];
  if (!preset) throw new ApiError(404, `no rgb presets for ${datacube}`);
  const p = getJSON<RGBViewerResponse>(
    `${dsPath(dataset)}/rgb/${encodeURIComponent(datacube)}/${preset.key}.json`,
  );
  rgbTemplateCache.set(key, p);
  return p;
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
    const meta = await getDatasetMeta(ds);
    const stretch = meta.stretches.includes(params.stretch) ? params.stretch : "log";
    const payload = await getJSON<ViewerResponse>(
      `${dsPath(ds)}/viewer/${encodeURIComponent(datacube)}/${stretch}/${channel}.json`,
    );
    payload.figure.data[0].colorscale = params.colorscale;
    return payload;
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
    const cube = await loadChannelCube(ds, datacube);
    const indices = [params.r, params.g, params.b];
    if (indices.some((index) => index < 0 || index >= cube.nChannels)) {
      throw new ApiError(400, `${ds}/${datacube} RGB channels`);
    }
    const planeSize = cube.ny * cube.nx;
    const template = await loadRgbTemplate(meta, ds, datacube);
    const rgb = composeRgb(
      cube.data.subarray(params.r * planeSize, (params.r + 1) * planeSize),
      cube.data.subarray(params.g * planeSize, (params.g + 1) * planeSize),
      cube.data.subarray(params.b * planeSize, (params.b + 1) * planeSize),
      params.method === "lupton" ? "lupton" : "percentile_asinh",
      params.softening,
    );
    const figure = {
      ...template.figure,
      layout: {
        ...template.figure.layout,
        images: (template.figure.layout.images as Record<string, unknown>[]).map(
          (image: Record<string, unknown>, index: number) =>
            index === 0
              ? { ...image, source: rgbToPngDataUrl(rgb, cube.nx, cube.ny) }
              : image,
        ),
      },
    };
    const filters = meta.filters[datacube];
    return {
      figure,
      r_filter: filters[params.r].name,
      g_filter: filters[params.g].name,
      b_filter: filters[params.b].name,
    };
  },
};
