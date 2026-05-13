"""Tests for statistics module."""

import numpy as np

from jellyscope.spec_analysis.stats import compute_clump_summary, compute_region_stats


def test_region_stats_normal(store):
    dc = store.get_datacube("nircam")
    mask = np.zeros(dc.spatial_shape, dtype=bool)
    mask[50:60, 50:60] = True
    stats = compute_region_stats(dc, mask, 0)
    assert stats["filter"] == "F070W"
    assert stats["n_pixels"] > 0
    assert isinstance(stats["mean"], float)
    assert isinstance(stats["median"], float)
    assert isinstance(stats["std"], float)
    assert isinstance(stats["min"], float)
    assert isinstance(stats["max"], float)
    assert isinstance(stats["sum"], float)


def test_region_stats_empty(store):
    dc = store.get_datacube("nircam")
    mask = np.zeros(dc.spatial_shape, dtype=bool)
    stats = compute_region_stats(dc, mask, 0)
    assert stats["n_pixels"] == 0
    assert stats["mean"] is None
    assert stats["median"] is None
    assert stats["std"] is None
    assert stats["min"] is None
    assert stats["max"] is None
    assert stats["sum"] is None


def test_clump_summary(store):
    dc = store.get_datacube("nircam")
    summary = compute_clump_summary(dc, store.clumps, 0)
    assert summary["clump_id"] == 0
    assert summary["component"] == "outside"
    assert summary["area_pix"] == 121
    assert summary["inside"] is False
    assert len(summary["channel_stats"]) == 20
    assert all(s["n_pixels"] > 0 for s in summary["channel_stats"])
