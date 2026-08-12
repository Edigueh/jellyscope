import type { Bootstrap } from "./types";

// Read the JSON the Jinja template injected. Falls back to an empty-ish shape
// so the dev entry (frontend/index.html) and headless renders don't crash.
export function readBootstrap(): Bootstrap {
  const el = document.getElementById("bootstrap");
  if (el?.textContent) {
    try {
      return JSON.parse(el.textContent) as Bootstrap;
    } catch {
      // fall through to default
    }
  }
  return {
    datasets: [],
    default_dataset: "",
    default_datacube: "",
    datacubes: [],
    filters: [],
    wavelengths: {},
  };
}
