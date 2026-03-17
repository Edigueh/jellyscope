"""Tests for FITS datacube handler."""

import numpy as np


def test_datacube_loads(store):
    dc = store.get_datacube("nircam")
    assert dc.shape == (20, 221, 172)
    assert dc.n_channels == 20
    assert dc.ny == 221
    assert dc.nx == 172


def test_filter_names_from_header(store):
    dc = store.get_datacube("nircam")
    assert dc.filter_names[0] == "F070W"
    assert dc.filter_names[-1] == "F480M"
    assert len(dc.filter_names) == 20


def test_get_slice(store):
    dc = store.get_datacube("nircam")
    s = dc.get_slice(0)
    assert s.shape == (221, 172)
    assert s.dtype == np.float64


def test_get_slice_by_name(store):
    dc = store.get_datacube("nircam")
    s = dc.get_slice_by_name("F200W")
    assert s.shape == (221, 172)


def test_get_spectrum_at_pixel(store):
    dc = store.get_datacube("nircam")
    spec = dc.get_spectrum_at_pixel(80, 100)
    assert spec.shape == (20,)


def test_to_json_slice(store):
    dc = store.get_datacube("nircam")
    js = dc.to_json_slice(0)
    assert len(js) == 221
    assert len(js[0]) == 172
    assert all(isinstance(v, (float, type(None))) for v in js[0])


def test_both_datacubes_available(store):
    assert "nircam" in store.list_datacubes()
    assert "nircam_matched" in store.list_datacubes()


def test_get_slice_out_of_range(store):
    import pytest

    dc = store.get_datacube("nircam")
    with pytest.raises(IndexError, match="out of range"):
        dc.get_slice(99)


def test_fallback_filter_names(store):
    dc = store.get_datacube("nircam")
    # Temporarily remove a filter key and test fallback
    original = dc.header.get("FILTER1")
    del dc.header["FILTER1"]
    names = dc._read_filter_names()
    assert names[0] == "CH1"
    assert names[1] == dc.filter_names[1]  # rest unchanged
    dc.header["FILTER1"] = original
