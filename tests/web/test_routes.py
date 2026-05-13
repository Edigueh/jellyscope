"""Tests for REST API routes."""

from http import HTTPStatus


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK
    assert b"Jellyscope" in resp.content


def test_list_datacubes(client):
    resp = client.get("/api/datacubes")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "nircam" in data["datacubes"]


def test_list_filters(client):
    resp = client.get("/api/filters/nircam")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert len(data["filters"]) == 20


def test_viewer_figure(client):
    resp = client.get("/api/viewer/nircam/7")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert len(data["figure"]["data"]) > 0


def test_list_clumps(client):
    resp = client.get("/api/clumps")
    data = resp.json()
    assert len(data["clumps"]) == 23

    resp = client.get("/api/clumps?component=disk")
    data = resp.json()
    assert all(c["component"] == "disk" for c in data["clumps"])


def test_get_clump_detail(client):
    resp = client.get("/api/clumps/0")
    data = resp.json()
    assert "properties" in data
    assert "boundary" in data


def test_pixel_clump_lookup(client):
    resp = client.get("/api/pixel/72/20/clump")
    data = resp.json()
    assert data["clump_id"] == 0


def test_list_clumps_with_inside_filter(client):
    resp = client.get("/api/clumps?inside=true")
    data = resp.json()
    assert all(c["inside"] is True for c in data["clumps"])

    resp = client.get("/api/clumps?inside=false")
    data = resp.json()
    assert all(c["inside"] is False for c in data["clumps"])


def test_viewer_all_nan():
    from unittest.mock import patch

    import numpy as np

    nan_slice = np.full((221, 172), np.nan)
    with patch("jellyscope.visualization.image_viewer.DataCube") as _:
        from jellyscope.visualization.image_viewer import _normalize_stretch

        result = _normalize_stretch(nan_slice)
        assert result.shape == (221, 172)


def test_viewer_stretch_lupton_asinh(client):
    resp = client.get("/api/viewer/nircam/7?stretch=lupton_asinh")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert len(data["figure"]["data"]) > 0


def test_viewer_stretch_default_is_log(client):
    resp_default = client.get("/api/viewer/nircam/7")
    resp_log = client.get("/api/viewer/nircam/7?stretch=log")
    assert resp_default.status_code == HTTPStatus.OK
    assert resp_log.status_code == HTTPStatus.OK
    assert resp_default.json() == resp_log.json()


def test_rgb_viewer_figure(client):
    resp = client.get("/api/viewer/nircam/rgb?r=17&g=7&b=0")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert data["r_filter"] == "F444W"
    assert data["g_filter"] == "F200W"
    assert data["b_filter"] == "F070W"
    assert data["figure"]["data"][0]["type"] == "image"


def test_rgb_viewer_with_softening(client):
    resp = client.get("/api/viewer/nircam/rgb?r=17&g=7&b=0&softening=12.0")
    assert resp.status_code == HTTPStatus.OK


def test_viewer_invalid_stretch(client):
    resp = client.get("/api/viewer/nircam/7?stretch=invalid")
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_rgb_viewer_invalid_channel(client):
    resp = client.get("/api/viewer/nircam/rgb?r=999&g=7&b=0")
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_viewer_invalid_channel_index(client):
    resp = client.get("/api/viewer/nircam/999")
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_clump_spectrum(client):
    resp = client.get("/api/clumps/0/spectrum/nircam")
    data = resp.json()
    assert "spectrum" in data
    assert "figure" in data
    assert len(data["spectrum"]["mean_flux"]) == 20


def test_pixel_spectrum(client):
    resp = client.get("/api/pixel/80/100/spectrum/nircam")
    data = resp.json()
    assert len(data["spectrum"]["fluxes"]) == 20


def test_region_spectrum(client):
    resp = client.post(
        "/api/region/spectrum/nircam",
        json={"rect": {"x0": 70, "y0": 15, "x1": 80, "y1": 25}},
    )
    data = resp.json()
    assert data["spectrum"]["n_pixels"] > 0


def test_compare_spectra(client):
    resp = client.post(
        "/api/compare/spectrum/nircam",
        json={"clump_ids": [0, 1, 3]},
    )
    data = resp.json()
    assert len(data["spectra"]) == 3
    assert len(data["figure"]["data"]) == 3
