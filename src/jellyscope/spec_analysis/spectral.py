"""Spectral extraction from datacubes for pixels, clumps, and arbitrary regions."""

import numpy as np

from jellyscope.config import NIRCAM_WAVELENGTHS
from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog


def _wavelengths_for(filter_names: list[str]) -> list[float]:
    """Map filter names to central wavelengths in microns."""
    return [NIRCAM_WAVELENGTHS.get(f, 0.0) for f in filter_names]


def extract_pixel_spectrum(datacube: DataCube, x: int, y: int) -> dict:
    """Extract spectrum at a single pixel.

    Returns dict with filter_names, wavelengths, and fluxes arrays.
    """
    fluxes: np.ndarray = datacube.get_spectrum_at_pixel(x, y)
    return {
        "filter_names": datacube.filter_names,
        "wavelengths": _wavelengths_for(datacube.filter_names),
        "fluxes": [float(f) if not np.isnan(f) else None for f in fluxes],
        "n_pixels": 1,
    }


def extract_clump_spectrum(datacube: DataCube, clumps: ClumpCatalog, clump_id: int) -> dict:
    """Mean spectrum for a clump region."""
    mask: np.ndarray = clumps.get_pixel_mask(clump_id)
    mean_flux, std_flux = datacube.get_mean_spectrum_for_mask(mask)
    return {
        "filter_names": datacube.filter_names,
        "wavelengths": _wavelengths_for(datacube.filter_names),
        "mean_flux": [float(f) if not np.isnan(f) else None for f in mean_flux],
        "std_flux": [float(f) if not np.isnan(f) else None for f in std_flux],
        "n_pixels": int(mask.sum()),
        "clump_id": clump_id,
    }


def extract_region_spectrum(datacube: DataCube, mask: np.ndarray) -> dict:
    """Mean spectrum for an arbitrary boolean mask (from lasso/rectangle selection)."""
    n_pixels = int(mask.sum())
    if n_pixels == 0:
        n_ch: int = datacube.n_channels
        return {
            "filter_names": datacube.filter_names,
            "wavelengths": _wavelengths_for(datacube.filter_names),
            "mean_flux": [None] * n_ch,
            "std_flux": [None] * n_ch,
            "n_pixels": 0,
        }
    mean_flux, std_flux = datacube.get_mean_spectrum_for_mask(mask)
    return {
        "filter_names": datacube.filter_names,
        "wavelengths": _wavelengths_for(datacube.filter_names),
        "mean_flux": [float(v) if not np.isnan(v) else None for v in mean_flux],
        "std_flux": [float(v) if not np.isnan(v) else None for v in std_flux],
        "n_pixels": n_pixels,
    }
