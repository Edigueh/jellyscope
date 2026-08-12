// Typed fetch wrappers for the 9 backend endpoints. Base path is per-dataset.
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

function dsBase(dataset: string): string {
  return `/api/datasets/${encodeURIComponent(dataset)}`;
}

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new ApiError(resp.status, url);
  }
  return (await resp.json()) as T;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    url: string,
  ) {
    super(`${status} for ${url}`);
    this.name = "ApiError";
  }
}

export const api = {
  datacubes: (ds: string) => getJSON<DatacubesResponse>(`${dsBase(ds)}/datacubes`),

  filters: (ds: string, datacube: string) =>
    getJSON<FiltersResponse>(`${dsBase(ds)}/filters/${encodeURIComponent(datacube)}`),

  clumps: (ds: string, component?: string) => {
    let url = `${dsBase(ds)}/clumps`;
    if (component) url += `?component=${encodeURIComponent(component)}`;
    return getJSON<ClumpsListResponse>(url);
  },

  clump: (ds: string, id: number) => getJSON<ClumpDetailResponse>(`${dsBase(ds)}/clumps/${id}`),

  separations: (ds: string) =>
    getJSON<ClumpSeparationsResponse>(`${dsBase(ds)}/clumps/separations`),

  pixelClump: (ds: string, x: number, y: number) =>
    getJSON<PixelClumpResponse>(`${dsBase(ds)}/pixel/${x}/${y}/clump`),

  viewerSingle: (
    ds: string,
    datacube: string,
    channel: number,
    params: { selected: string; colorscale: string; stretch: string },
  ) => {
    const q = new URLSearchParams(params).toString();
    return getJSON<ViewerResponse>(
      `${dsBase(ds)}/viewer/${encodeURIComponent(datacube)}/${channel}?${q}`,
    );
  },

  viewerRGB: (
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
  ) => {
    const q = new URLSearchParams({
      r: String(params.r),
      g: String(params.g),
      b: String(params.b),
      selected: params.selected,
      method: params.method,
      softening: String(params.softening),
    }).toString();
    return getJSON<RGBViewerResponse>(
      `${dsBase(ds)}/viewer/${encodeURIComponent(datacube)}/rgb?${q}`,
    );
  },
};
