import { getDatasetMeta } from "./api";
import type { Bootstrap } from "./types";

interface StaticManifest {
  datasets: string[];
  default: string;
  wavelengths: Record<string, number>;
  stretches: string[];
  rgb_presets: string[][];
}

// Fetch the static manifest + the default dataset's meta so we can populate
// the initial state with something meaningful (matches what the Jinja
// bootstrap block previously provided).
export async function readBootstrap(): Promise<Bootstrap> {
  try {
    const manifest = (await (await fetch("./data/manifest.json")).json()) as StaticManifest;
    const defaultDs = manifest.default;
    if (!defaultDs) return emptyBootstrap();
    const meta = await getDatasetMeta(defaultDs);
    const defaultCube = meta.datacubes[0];
    return {
      datasets: manifest.datasets,
      default_dataset: defaultDs,
      default_datacube: defaultCube,
      datacubes: meta.datacubes,
      filters: (meta.filters[defaultCube] ?? []).map((f) => f.name),
      wavelengths: manifest.wavelengths,
    };
  } catch {
    return emptyBootstrap();
  }
}

function emptyBootstrap(): Bootstrap {
  return {
    datasets: [],
    default_dataset: "",
    default_datacube: "",
    datacubes: [],
    filters: [],
    wavelengths: {},
  };
}
