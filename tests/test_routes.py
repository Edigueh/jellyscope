"""Tests for Flask routes."""

import json


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Jellyscope" in resp.data


def test_list_datacubes(client):
    resp = client.get("/api/datacubes")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "nircam" in data["datacubes"]


def test_list_filters(client):
    resp = client.get("/api/filters/nircam")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["filters"]) == 20


def test_viewer_figure(client):
    resp = client.get("/api/viewer/nircam/7")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "figure" in data
    assert len(data["figure"]["data"]) > 0


def test_list_clumps(client):
    resp = client.get("/api/clumps")
    data = resp.get_json()
    assert len(data["clumps"]) == 23


def test_filter_clumps_by_component(client):
    resp = client.get("/api/clumps?component=disk")
    data = resp.get_json()
    assert all(c["component"] == "disk" for c in data["clumps"])


def test_get_clump_detail(client):
    resp = client.get("/api/clumps/0")
    data = resp.get_json()
    assert "properties" in data
    assert "boundary" in data


def test_clump_spectrum(client):
    resp = client.get("/api/clumps/0/spectrum/nircam")
    data = resp.get_json()
    assert "spectrum" in data
    assert "figure" in data
    assert len(data["spectrum"]["mean_flux"]) == 20


def test_pixel_clump_lookup(client):
    resp = client.get("/api/pixel/72/20/clump")
    data = resp.get_json()
    assert data["clump_id"] == 0


def test_pixel_spectrum(client):
    resp = client.get("/api/pixel/80/100/spectrum/nircam")
    data = resp.get_json()
    assert len(data["spectrum"]["fluxes"]) == 20


def test_region_spectrum(client):
    resp = client.post(
        "/api/region/spectrum/nircam",
        data=json.dumps({"rect": {"x0": 70, "y0": 15, "x1": 80, "y1": 25}}),
        content_type="application/json",
    )
    data = resp.get_json()
    assert data["spectrum"]["n_pixels"] > 0


def test_compare_spectra(client):
    resp = client.post(
        "/api/compare/spectrum/nircam",
        data=json.dumps({"clump_ids": [0, 1, 3]}),
        content_type="application/json",
    )
    data = resp.get_json()
    assert len(data["spectra"]) == 3
    assert len(data["figure"]["data"]) == 3
