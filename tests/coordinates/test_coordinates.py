"""Tests for src/jellyscope/data/model/coordinates.py."""

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS

from jellyscope.data.model.coordinates import (
    arcsec_axis,
    image_arcsec_extent,
    image_axis_bounds,
    pixel_scale_arcsec,
    pixel_to_skycoord,
    pixels_to_radec_arrays,
    skycoord_separation_arcsec,
)


def _make_wcs(ra0_deg: float = 180.0, dec0_deg: float = 0.0, pix_scale_arcsec: float = 1.0) -> WCS:
    """Synthetic TAN WCS at known RA/Dec with a uniform pixel scale."""
    w = WCS(naxis=2)
    w.wcs.crpix = [50.5, 50.5]
    w.wcs.crval = [ra0_deg, dec0_deg]
    deg_per_pix = pix_scale_arcsec / 3600.0
    w.wcs.cdelt = [-deg_per_pix, deg_per_pix]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return w


def test_pixel_scale_arcsec_matches_construction():
    w = _make_wcs(pix_scale_arcsec=0.5)
    assert pixel_scale_arcsec(w) == pytest.approx(0.5, rel=1e-6)


def test_pixel_to_skycoord_at_reference():
    w = _make_wcs(ra0_deg=180.0, dec0_deg=0.0)
    # CRPIX is 1-based; astropy pixel_to_world uses 0-based: ref pixel = crpix - 1
    sc = pixel_to_skycoord(49.5, 49.5, w)
    assert sc.ra.deg == pytest.approx(180.0, abs=1e-6)
    assert sc.dec.deg == pytest.approx(0.0, abs=1e-6)


def test_pixel_to_skycoord_vector():
    w = _make_wcs()
    xs = np.array([49.5, 50.5, 51.5])
    ys = np.array([49.5, 49.5, 49.5])
    sc = pixel_to_skycoord(xs, ys, w)
    assert sc.shape == (3,)
    # Stepping +1 pixel in x with a -1 deg-per-pixel-x CD entry should decrease RA.
    diffs = np.diff(sc.ra.arcsec)
    assert np.all(diffs < 0)


def test_skycoord_separation_arcsec_one_pixel_apart():
    w = _make_wcs(pix_scale_arcsec=1.0)
    c1 = pixel_to_skycoord(49.5, 49.5, w)
    c2 = pixel_to_skycoord(50.5, 49.5, w)
    sep = skycoord_separation_arcsec(c1, c2)
    assert sep == pytest.approx(1.0, abs=1e-3)


def test_skycoord_separation_handles_known_pair():
    c1 = SkyCoord(ra=10.0 * u.deg, dec=0.0 * u.deg)
    c2 = SkyCoord(ra=10.0 * u.deg, dec=(1.0 / 3600.0) * u.deg)
    sep = skycoord_separation_arcsec(c1, c2)
    assert sep == pytest.approx(1.0, abs=1e-6)


def test_pixels_to_radec_arrays_vector_input():
    w = _make_wcs(ra0_deg=180.0, dec0_deg=0.0, pix_scale_arcsec=1.0)
    xs = np.array([49.5, 50.5, 51.5])
    ys = np.array([49.5, 49.5, 49.5])
    ra, dec, finite = pixels_to_radec_arrays(xs, ys, w)

    assert ra.shape == (3,)
    assert dec.shape == (3,)
    assert finite.shape == (3,)
    assert finite.all()
    # Reference pixel must round-trip to crval.
    assert ra[0] == pytest.approx(180.0, abs=1e-6)
    assert dec[0] == pytest.approx(0.0, abs=1e-6)


def test_pixels_to_radec_arrays_scalar_lifted_to_length_1():
    w = _make_wcs()
    ra, dec, finite = pixels_to_radec_arrays(49.5, 49.5, w)
    assert ra.shape == (1,)
    assert dec.shape == (1,)
    assert finite.tolist() == [True]


def test_pixels_to_radec_arrays_finite_mask_marks_nan():
    # Pass NaN inputs — astropy returns NaN sky coords; mask must mark them.
    w = _make_wcs()
    xs = np.array([49.5, np.nan])
    ys = np.array([49.5, 49.5])
    ra, dec, finite = pixels_to_radec_arrays(xs, ys, w)
    assert finite.tolist() == [True, False]
    assert np.isfinite(ra[0])
    assert not np.isfinite(ra[1])
    assert np.isfinite(dec[0])
    assert not np.isfinite(dec[1])


def test_arcsec_axis_centered_odd_length():
    axis = arcsec_axis(5, 0.5)
    # 5 cells, scale 0.5"/pix => [-1.0, -0.5, 0.0, 0.5, 1.0]
    assert axis.tolist() == pytest.approx([-1.0, -0.5, 0.0, 0.5, 1.0])


def test_arcsec_axis_centered_even_length():
    axis = arcsec_axis(4, 1.0)
    # ref = (4-1)/2 = 1.5 => offsets -1.5, -0.5, 0.5, 1.5
    assert axis.tolist() == pytest.approx([-1.5, -0.5, 0.5, 1.5])


def test_image_arcsec_extent_matches_axis_span():
    nx, ny, sec = 170, 155, 0.02
    extent = image_arcsec_extent(nx, ny, sec)
    assert extent["x"] == pytest.approx(-nx * sec / 2.0)
    assert extent["y"] == pytest.approx(-ny * sec / 2.0)
    assert extent["sizex"] == pytest.approx(nx * sec)
    assert extent["sizey"] == pytest.approx(ny * sec)
    # Image lower-left to upper-right spans the full FOV.
    assert extent["x"] + extent["sizex"] == pytest.approx(nx * sec / 2.0)


def test_image_axis_bounds_arcsec_branch():
    nx, ny, sec = 170, 155, 0.02
    bounds = image_axis_bounds(nx, ny, sec)
    assert bounds["x"] == pytest.approx((-nx * sec / 2.0, nx * sec / 2.0))
    assert bounds["y"] == pytest.approx((-ny * sec / 2.0, ny * sec / 2.0))
    # Default min span = 5 pixels.
    assert bounds["x_min_span"] == pytest.approx(5 * sec)
    assert bounds["y_min_span"] == pytest.approx(5 * sec)


def test_image_axis_bounds_pixel_fallback():
    nx, ny = 170, 155
    bounds = image_axis_bounds(nx, ny, None)
    assert bounds["x"] == (0.0, float(nx))
    assert bounds["y"] == (0.0, float(ny))
    assert np.isclose(bounds["x_min_span"], 5.0, rtol=1e-09, atol=1e-09)
    assert np.isclose(bounds["y_min_span"], 5.0, rtol=1e-09, atol=1e-09)


def test_image_axis_bounds_custom_min_span_pixels():
    nx, ny, sec = 100, 100, 0.04
    bounds = image_axis_bounds(nx, ny, sec, min_span_pixels=10)
    assert bounds["x_min_span"] == pytest.approx(10 * sec)
    assert bounds["y_min_span"] == pytest.approx(10 * sec)
