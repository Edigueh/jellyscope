"""Summary statistics for selected regions."""

import numpy as np

from ..data.clumps import ClumpCatalog
from ..data.fits_handler import DataCube


def compute_region_stats(datacube: DataCube, mask: np.ndarray, channel_index: int) -> dict:
    """Compute statistics for a spatial region at a given filter channel."""
    slice_data = datacube.get_slice(channel_index)
    values = slice_data[mask]
    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        return {
            "filter": datacube.filter_names[channel_index],
            "n_pixels": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "sum": None,
        }
    return {
        "filter": datacube.filter_names[channel_index],
        "n_pixels": len(valid),
        "mean": float(np.mean(valid)),
        "median": float(np.median(valid)),
        "std": float(np.std(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "sum": float(np.sum(valid)),
    }


def compute_clump_summary(datacube: DataCube, clumps: ClumpCatalog, clump_id: int) -> dict:
    """Full summary: clump properties + per-channel statistics."""
    props = clumps.get_clump(clump_id)
    mask = clumps.get_pixel_mask(clump_id)
    channel_stats = [compute_region_stats(datacube, mask, i) for i in range(datacube.n_channels)]
    return {
        "clump_id": clump_id,
        "component": props.component,
        "area_pix": props.area_pix,
        "area_kpc2": props.area_kpc2,
        "r_eff_kpc": props.r_eff_kpc,
        "inside": props.inside,
        "channel_stats": channel_stats,
    }
