"""Summary statistics for selected regions."""

import numpy as np

from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog, ClumpProperties


def compute_region_stats(datacube: DataCube, mask: np.ndarray, channel_idx: int) -> dict:
    """Compute statistics for a spatial region at a given filter channel."""
    slice_data: np.ndarray = datacube.get_slice_by_channel_index(channel_idx)
    values = slice_data[mask]
    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        return {
            "filter": datacube.filter_names[channel_idx],
            "n_pixels": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "sum": None,
        }
    return {
        "filter": datacube.filter_names[channel_idx],
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
    props: ClumpProperties = clumps.get_clump_by_id(clump_id)
    mask = clumps.get_pixel_mask(clump_id)
    channel_stats: list[dict] = [
        compute_region_stats(datacube, mask, i) for i in range(datacube.n_channels)
    ]
    return {
        "clump_id": clump_id,
        "component": props.component,
        "area_pix": props.area_pix,
        "area_kpc2": props.area_kpc2,
        "r_eff_kpc2": props.r_eff_kpc2,
        "inside": props.inside,
        "channel_stats": channel_stats,
    }
