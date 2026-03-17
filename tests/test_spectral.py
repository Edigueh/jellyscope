"""Tests for spectral extraction."""

from jellyscope.analysis.spectral import (
    extract_clump_spectrum,
    extract_pixel_spectrum,
    extract_region_spectrum,
)


def test_pixel_spectrum(store):
    dc = store.get_datacube("nircam")
    result = extract_pixel_spectrum(dc, 80, 100)
    assert len(result["fluxes"]) == 20
    assert len(result["wavelengths"]) == 20
    assert result["n_pixels"] == 1


def test_clump_spectrum(store):
    dc = store.get_datacube("nircam")
    result = extract_clump_spectrum(dc, store.clumps, 0)
    assert len(result["mean_flux"]) == 20
    assert len(result["std_flux"]) == 20
    assert result["n_pixels"] == 121
    assert result["clump_id"] == 0


def test_region_spectrum_with_mask(store):
    import numpy as np

    dc = store.get_datacube("nircam")
    mask = np.zeros(dc.spatial_shape, dtype=bool)
    mask[50:60, 50:60] = True
    result = extract_region_spectrum(dc, mask)
    assert result["n_pixels"] == 100
    assert len(result["mean_flux"]) == 20


def test_empty_region_spectrum(store):
    import numpy as np

    dc = store.get_datacube("nircam")
    mask = np.zeros(dc.spatial_shape, dtype=bool)
    result = extract_region_spectrum(dc, mask)
    assert result["n_pixels"] == 0
