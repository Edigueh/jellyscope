// API types — mirror src/jellyscope/model/schemas.py. Keep in sync by hand;
// the wire contract is small and stable.

export interface FilterInfo {
  index: number;
  name: string;
  wavelength: number;
}

export interface ClumpListItem {
  clump_id: number;
  x0: number;
  y0: number;
  area_pix: number;
  component: string;
  inside: boolean;
}

export interface DatasetsResponse {
  datasets: string[];
  default: string;
}
export interface DatacubesResponse {
  datacubes: string[];
}
export interface FiltersResponse {
  filters: FilterInfo[];
}
export interface ClumpsListResponse {
  clumps: ClumpListItem[];
}

export interface ClumpPropertyEntry {
  label: string;
  value: string;
}
export interface ClumpDetailResponse {
  properties: { entries: ClumpPropertyEntry[] };
  boundary: [number, number][];
}

export interface PixelClumpResponse {
  clump_id: number | null;
}

export interface ClumpSeparation {
  clump_a: number;
  clump_b: number;
  sep_arcsec: number;
  sep_pc: number | null;
}
export interface ClumpSeparationsResponse {
  distance_mpc: number | null;
  pairs: ClumpSeparation[];
}

// Plotly figure as delivered by the backend. We treat data/layout loosely —
// the science core reads specific keys (meta.wcs, meta.imageBounds, trace
// names) but Plotly owns the full shape.
export interface Figure {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: Record<string, any>[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layout: Record<string, any>;
}

export interface ViewerResponse {
  figure: Figure;
  filter_name: string;
}
export interface RGBViewerResponse {
  figure: Figure;
  r_filter: string;
  g_filter: string;
  b_filter: string;
}

// Injected by the Jinja template as a <script id="bootstrap"> JSON block.
export interface Bootstrap {
  datasets: string[];
  default_dataset: string;
  default_datacube: string;
  datacubes: string[];
  filters: string[];
  wavelengths: Record<string, number>;
}
