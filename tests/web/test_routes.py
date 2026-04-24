"""Tests for REST API routes."""

from http import HTTPStatus


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
