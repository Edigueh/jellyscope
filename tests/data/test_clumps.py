"""Tests for clump catalog."""

import logging

import numpy as np
import pytest

from jellyscope.data.data_store import DataStore
from jellyscope.data.model.clumps import ClumpProperties


@pytest.mark.usefixtures("store")
class TestClumps:
    @pytest.fixture(autouse=True)
    def setup(self, store: DataStore):
        self.store: DataStore = store

    def test_clump_count(self):
        assert len(self.store.clumps.list_clumps()) == 23

    def test_clump_properties(self):
        cid: int = 0
        c: ClumpProperties = self.store.clumps.get_clump_by_id(cid)
        assert c.clump_id == cid
        assert c.area_pix == 121
        assert c.component == "outside"
        assert c.inside is False

    def test_pixel_mask(self):
        cid: int = 0
        c: ClumpProperties = self.store.clumps.get_clump_by_id(cid)
        mask: np.ndarray = self.store.clumps.get_pixel_mask(cid)
        assert mask.shape == (221, 172)
        assert mask.dtype == bool
        assert mask.sum() == c.area_pix

    def test_clump_at_pixel(self):
        # Clump 0 centroid is near (71.8, 19.9)
        cid: int = self.store.clumps.get_clump_id_at_pixel(72, 20)
        assert cid == 0

    def test_no_clump_at_empty_pixel(self):
        cid: int = self.store.clumps.get_clump_id_at_pixel(0, 0)
        assert cid is None

    def test_boundary_coords(self):
        boundary: list[tuple[float, float]] = self.store.clumps.get_boundary_coords(0)
        assert len(boundary) >= 3
        # start == end
        assert boundary[0] == boundary[-1]

    def test_filter_by_component(self):
        disk: list[ClumpProperties] = self.store.clumps.filter_clumps(component="disk")
        outside: list[ClumpProperties] = self.store.clumps.filter_clumps(component="outside")
        for c in disk:
            logging.info(c.component)
        assert all(c.component == "disk" for c in disk)
        assert all(c.component == "outside" for c in outside)
        assert len(disk) + len(outside) == 23

    def test_filter_by_inside(self):
        inside: list[ClumpProperties] = self.store.clumps.filter_clumps(inside=True)
        outside: list[ClumpProperties] = self.store.clumps.filter_clumps(inside=False)
        for c in inside:
            logging.info(c.component)
        assert all(c.inside is True for c in inside)
        assert all(c.inside is False for c in outside)
        assert len(inside) + len(outside) == 23

    def test_combined_mask(self):
        cid1, cid2 = 0, 1
        c1: ClumpProperties = self.store.clumps.get_clump_by_id(cid1)
        c2: ClumpProperties = self.store.clumps.get_clump_by_id(cid2)
        mask: np.ndarray = self.store.clumps.get_combined_mask([cid1, cid2])
        assert mask.sum() == c1.area_pix + c2.area_pix

    def test_pixel_out_of_bounds(self):
        assert self.store.clumps.get_clump_id_at_pixel(-1, -1) is None
        assert self.store.clumps.get_clump_id_at_pixel(9999, 9999) is None

    def test_boundary_cache_hit(self):
        b1 = self.store.clumps.get_boundary_coords(0)
        b2 = self.store.clumps.get_boundary_coords(0)
        assert b1 is b2

    def test_get_all_boundaries(self):
        boundaries = self.store.clumps.get_all_boundaries()
        assert len(boundaries.keys()) == 23

    def test_small_clump_boundary(self, tmp_path):
        import pandas as pd

        from jellyscope.data.model.clumps import ClumpCatalog

        props_df = pd.DataFrame(
            [
                {
                    "clump_id": 99,
                    "area_pix": 2,
                    "area_arcsec2": 0.1,
                    "r_eff_arcsec": 0.05,
                    "x0": 5.0,
                    "y0": 5.0,
                    "area_kpc2": 0.01,
                    "r_eff_kpc": 0.005,
                    "inside": True,
                    "component": "disk",
                }
            ]
        )

        pixels_df = pixels_df = pd.DataFrame(
            [{"clump_id": 99, "x": 5, "y": 5}, {"clump_id": 99, "x": 6, "y": 5}]
        )
        props_df.to_csv(tmp_path / "props.csv", index=False)
        pixels_df.to_csv(tmp_path / "pixels.csv", index=False)

        catalog = ClumpCatalog(tmp_path / "props.csv", tmp_path / "pixels.csv", (10, 10))
        boundary = catalog.get_boundary_coords(99)
        assert len(boundary) >= 2
        assert boundary[0] == boundary[-1]

    def test_qhull_error_fallback(self):
        from unittest.mock import patch

        from scipy.spatial import QhullError

        # Clear cache to recompute.
        self.store.clumps._boundaries.pop(0, None)
        with patch("jellyscope.data.model.clumps.ConvexHull", side_effect=QhullError("mock")):
            boundary = self.store.clumps.get_boundary_coords(0)
            assert len(boundary) >= 2
            assert boundary[0] == boundary[-1]

    def test_to_properties_list(self):
        props: list[dict] = self.store.clumps.to_properties_list()
        assert len(props) == 23
        assert all(isinstance(p, dict) for p in props)
        keys = {
            "clump_id",
            "area_pix",
            "area_arcsec2",
            "r_eff_arcsec",
            "x0",
            "y0",
            "area_kpc2",
            "r_eff_kpc",
            "inside",
            "component",
        }
        assert all(keys <= set(p.keys()) for p in props)
