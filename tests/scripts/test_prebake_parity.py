"""Parity: prebaked JSONs must equal live FastAPI responses byte-for-byte.

Guards against silent drift when someone edits a figure builder without
updating the prebake path. Runs the bake on the real ``data/`` dir into a
tmp path, then compares three anchor payloads against the TestClient.
"""

from __future__ import annotations

import gzip
import json
from http import HTTPStatus
from pathlib import Path

import numpy as np
import pytest

from jellyscope.data.model.datacube import DataCube
from scripts.prebake import bake


@pytest.fixture(scope="module")
def baked(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("bake")
    bake(Path("data"), out)
    return out


def _load_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def test_viewer_parity(client, baked: Path) -> None:
    resp = client.get("/api/datasets/abell2744_J1/viewer/nircam/7?stretch=log")
    assert resp.status_code == HTTPStatus.OK
    baked_payload = _load_json(baked / "abell2744_J1" / "viewer" / "nircam" / "log" / "7.json")
    assert resp.json() == baked_payload


def test_rgb_parity(client, baked: Path) -> None:
    resp = client.get("/api/datasets/abell2744_J1/viewer/nircam/rgb?r=17&g=7&b=0")
    assert resp.status_code == HTTPStatus.OK
    baked_payload = _load_json(baked / "abell2744_J1" / "rgb" / "nircam" / "17-7-0.json")
    assert resp.json() == baked_payload


def test_clump_detail_parity(client, baked: Path) -> None:
    resp = client.get("/api/datasets/abell2744_J1/clumps/0")
    assert resp.status_code == HTTPStatus.OK
    baked_payload = _load_json(baked / "abell2744_J1" / "clump" / "0.json")
    assert resp.json() == baked_payload


def test_clumps_list_parity(client, baked: Path) -> None:
    resp = client.get("/api/datasets/abell2744_J1/clumps")
    assert resp.status_code == HTTPStatus.OK
    baked_payload = _load_json(baked / "abell2744_J1" / "clumps.json")
    assert resp.json() == baked_payload


def test_prebaked_ambiguous_pixel(baked: Path) -> None:
    with gzip.open(baked / "abell2744_J1" / "pixel_index.bin.gz", "rb") as fh:
        raw = fh.read()
    ny, nx = np.frombuffer(raw[:8], dtype=np.int32)
    grid = np.frombuffer(raw[8:], dtype=np.int16).reshape((ny, nx))
    assert grid[74, 167] == -2


def test_prebaked_channel_cube(baked: Path) -> None:
    path = baked / "abell2744_J1" / "channels" / "nircam.bin.gz"
    with gzip.open(path, "rb") as fh:
        raw = fh.read()

    header = np.frombuffer(raw[:16], dtype="<i4")
    assert header.tolist() == [1, 20, 146, 192]
    payload = np.frombuffer(raw[16:], dtype="<f8").reshape(tuple(header[1:]))
    expected = DataCube("data/abell2744_J1/cut_datacube_nircam.fits").data
    np.testing.assert_array_equal(payload, expected)


def test_separations_parity(client, baked: Path) -> None:
    resp = client.get("/api/datasets/abell2744_J1/clumps/separations")
    assert resp.status_code == HTTPStatus.OK
    baked_payload = _load_json(baked / "abell2744_J1" / "separations.json")
    assert resp.json() == baked_payload


def test_manifest_lists_all_datasets(client, baked: Path) -> None:
    manifest = _load_json(baked / "manifest.json")
    live = client.get("/api/datasets").json()
    assert set(manifest["datasets"]) == set(live["datasets"])
    assert manifest["default"] == live["default"]
