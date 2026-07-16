"""Tests for REST API routes."""

from http import HTTPStatus

import pytest

DS = "A2744_F1228"
BASE = f"/api/datasets/{DS}"


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK
    assert b"Jellyscope" in resp.content


def test_list_datasets(client):
    resp = client.get("/api/datasets")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert DS in data["datasets"]
    assert data["default"] == DS


def test_unknown_dataset_404(client):
    resp = client.get("/api/datasets/does_not_exist/datacubes")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_list_datacubes(client):
    resp = client.get(f"{BASE}/datacubes")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "nircam" in data["datacubes"]


def test_list_filters(client):
    resp = client.get(f"{BASE}/filters/nircam")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert len(data["filters"]) == 20


def test_viewer_figure(client):
    resp = client.get(f"{BASE}/viewer/nircam/7")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert len(data["figure"]["data"]) > 0


def test_list_clumps(client):
    resp = client.get(f"{BASE}/clumps")
    data = resp.json()
    assert len(data["clumps"]) == 23

    resp = client.get(f"{BASE}/clumps?component=disk")
    data = resp.json()
    assert all(c["component"] == "disk" for c in data["clumps"])


def test_get_clump_detail(client):
    resp = client.get(f"{BASE}/clumps/0")
    data = resp.json()
    assert "properties" in data
    assert "boundary" in data
    assert isinstance(data["properties"]["entries"], list)
    assert len(data["properties"]["entries"]) > 0


def test_pixel_clump_lookup(client):
    resp = client.get(f"{BASE}/pixel/72/20/clump")
    data = resp.json()
    assert data["clump_id"] == 0


def test_list_clumps_with_inside_filter(client):
    resp = client.get(f"{BASE}/clumps?inside=true")
    data = resp.json()
    assert all(c["inside"] is True for c in data["clumps"])

    resp = client.get(f"{BASE}/clumps?inside=false")
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
    resp = client.get(f"{BASE}/viewer/nircam/7?stretch=lupton_asinh")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert len(data["figure"]["data"]) > 0


def test_viewer_stretch_default_is_log(client):
    resp_default = client.get(f"{BASE}/viewer/nircam/7")
    resp_log = client.get(f"{BASE}/viewer/nircam/7?stretch=log")
    assert resp_default.status_code == HTTPStatus.OK
    assert resp_log.status_code == HTTPStatus.OK
    assert resp_default.json() == resp_log.json()


def test_rgb_viewer_figure(client):
    resp = client.get(f"{BASE}/viewer/nircam/rgb?r=17&g=7&b=0")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert "figure" in data
    assert data["r_filter"] == "F444W"
    assert data["g_filter"] == "F200W"
    assert data["b_filter"] == "F070W"
    assert data["figure"]["data"][0]["type"] == "heatmap"
    assert "images" in data["figure"]["layout"]


def test_rgb_viewer_with_softening(client):
    resp = client.get(f"{BASE}/viewer/nircam/rgb?r=17&g=7&b=0&softening=12.0")
    assert resp.status_code == HTTPStatus.OK


def test_viewer_invalid_stretch(client):
    resp = client.get(f"{BASE}/viewer/nircam/7?stretch=invalid")
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_rgb_viewer_invalid_channel(client):
    resp = client.get(f"{BASE}/viewer/nircam/rgb?r=999&g=7&b=0")
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_viewer_invalid_channel_index(client):
    resp = client.get(f"{BASE}/viewer/nircam/999")
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_clump_separations(client):
    resp = client.get(f"{BASE}/clumps/separations")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    n = 23
    assert len(data["pairs"]) == n * (n - 1) // 2
    assert data["distance_mpc"] is None
    for pair in data["pairs"]:
        assert pair["clump_a"] < pair["clump_b"]
        assert pair["sep_arcsec"] > 0
        assert pair["sep_pc"] is None


def test_clump_separations_matches_skycoord(client):
    from astropy import units as u
    from astropy.coordinates import SkyCoord

    def _lookup(entries: list[dict], label: str) -> str:
        return next(e["value"] for e in entries if e["label"] == label)

    detail_a = client.get(f"{BASE}/clumps/0").json()["properties"]["entries"]
    detail_b = client.get(f"{BASE}/clumps/1").json()["properties"]["entries"]
    ra_a = float(_lookup(detail_a, "RA (deg)"))
    dec_a = float(_lookup(detail_a, "Dec (deg)"))
    ra_b = float(_lookup(detail_b, "RA (deg)"))
    dec_b = float(_lookup(detail_b, "Dec (deg)"))
    expected = (
        SkyCoord(ra=ra_a * u.deg, dec=dec_a * u.deg)
        .separation(SkyCoord(ra=ra_b * u.deg, dec=dec_b * u.deg))
        .arcsec
    )

    resp = client.get(f"{BASE}/clumps/separations")
    pair = next(p for p in resp.json()["pairs"] if p["clump_a"] == 0 and p["clump_b"] == 1)
    # Properties panel formats RA/Dec to 6 decimal places; that drops ~1e-6 deg
    # of precision (~3.6 mas), so allow ~10 mas tolerance on a ~1.5" baseline.
    assert pair["sep_arcsec"] == pytest.approx(expected, abs=0.01)


def test_clump_detail_has_radec(client):
    resp = client.get(f"{BASE}/clumps/0")
    entries = resp.json()["properties"]["entries"]
    by_label = {e["label"]: e["value"] for e in entries}
    assert "RA (deg)" in by_label
    assert "Dec (deg)" in by_label
    assert by_label["RA (deg)"] != "—"
    assert by_label["Dec (deg)"] != "—"
