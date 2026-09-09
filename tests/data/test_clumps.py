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
        self.clumps = store.get_dataset("abell2744_J1").clumps

    def test_clump_count(self):
        assert len(self.clumps.list_clumps()) == 53

    def test_clump_properties(self):
        cid: int = 0
        c: ClumpProperties = self.clumps.get_clump_by_id(cid)
        assert c.clump_id == cid
        assert c.area_pix == 8
        assert c.component == "disk"
        # New IC schema — the ``inside`` field isn't provided.
        assert c.inside is None

    def test_pixel_mask(self):
        cid: int = 0
        c: ClumpProperties = self.clumps.get_clump_by_id(cid)
        mask: np.ndarray = self.clumps.get_pixel_mask(cid)
        assert mask.shape == (146, 192)
        assert mask.dtype == bool
        assert mask.sum() == c.area_pix

    def test_clump_at_pixel(self):
        # Clump 0 centroid is near (86.75, 26.5); pixel (85, 25) is inside its mask.
        cid: int = self.clumps.get_clump_id_at_pixel(85, 25)
        assert cid == 0

    def test_no_clump_at_empty_pixel(self):
        cid: int = self.clumps.get_clump_id_at_pixel(0, 0)
        assert cid is None

    def test_boundary_coords(self):
        boundary: list[tuple[float, float]] = self.clumps.get_boundary_coords(0)
        assert len(boundary) >= 3
        # start == end
        assert boundary[0] == boundary[-1]

    def test_filter_by_component(self):
        disk: list[ClumpProperties] = self.clumps.filter_clumps(component="disk")
        outside: list[ClumpProperties] = self.clumps.filter_clumps(component="outside")
        for c in disk:
            logging.info(c.component)
        assert all(c.component == "disk" for c in disk)
        assert all(c.component == "outside" for c in outside)
        # Every clump in this dataset is either disk or outside.
        assert len(disk) + len(outside) == 53

    def test_filter_by_inside_excludes_none(self):
        # New IC schema has no ``inside`` column → every clump is None →
        # both filter polarities must return an empty list.
        assert self.clumps.filter_clumps(inside=True) == []
        assert self.clumps.filter_clumps(inside=False) == []

    def test_pixel_out_of_bounds(self):
        assert self.clumps.get_clump_id_at_pixel(-1, -1) is None
        assert self.clumps.get_clump_id_at_pixel(9999, 9999) is None

    def test_boundary_cache_hit(self):
        b1 = self.clumps.get_boundary_coords(0)
        b2 = self.clumps.get_boundary_coords(0)
        assert b1 is b2

    def test_get_all_boundaries(self):
        boundaries = self.clumps.get_all_boundaries()
        assert len(boundaries.keys()) == 53

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
        self.clumps._boundaries.pop(0, None)
        with patch("jellyscope.data.model.clumps.ConvexHull", side_effect=QhullError("mock")):
            boundary = self.clumps.get_boundary_coords(0)
            assert len(boundary) >= 2
            assert boundary[0] == boundary[-1]

    def test_skycoords_attached(self):
        # DataStore attaches RA/Dec on load when WCS is celestial.
        coords = self.clumps.centroid_skycoords()
        assert coords is not None
        assert len(coords) == 53

        for c in self.clumps.list_clumps():
            assert c.ra_deg is not None
            assert c.dec_deg is not None
            assert -90.0 <= c.dec_deg <= 90.0
            assert 0.0 <= c.ra_deg <= 360.0


def test_new_schema_loads(tmp_path):
    """New IC schema (mass/sfr_avg/...) lacks r_eff_arcsec, r_eff_kpc, inside.

    Loader must accept the reduced column set and leave the missing fields
    as ``None`` on the resulting ClumpProperties.
    """
    import pandas as pd

    from jellyscope.data.model.clumps import ClumpCatalog

    props_df = pd.DataFrame(
        [
            {
                "clump_id": 1,
                "mass": 8.5,
                "logzsol": -0.3,
                "dust2": 0.1,
                "tage": 0.4,
                "gas_logu": -2.5,
                "area_kpc2": 0.02,
                "component": "disk",
                "sfr_avg": 0.005,
                "ssfr_avg": 1.6e-10,
                "area_pix": 5,
                "area_arcsec2": 0.2,
                "x0": 3.0,
                "y0": 3.0,
                "ra0": 3.6,
                "dec0": -30.4,
            }
        ]
    )
    pixels_df = pd.DataFrame([{"clump_id": 1, "x": 3, "y": 3}, {"clump_id": 1, "x": 4, "y": 3}])
    props_df.to_csv(tmp_path / "props.csv", index=False)
    pixels_df.to_csv(tmp_path / "pixels.csv", index=False)

    catalog = ClumpCatalog(tmp_path / "props.csv", tmp_path / "pixels.csv", (10, 10))
    c = catalog.get_clump_by_id(1)

    # Legacy-only fields absent → None.
    assert c.r_eff_arcsec is None
    assert c.r_eff_kpc is None
    assert c.inside is None
    # New schema fields populated.
    assert c.mass == pytest.approx(8.5)
    assert c.sfr_avg == pytest.approx(0.005)
    assert c.ssfr_avg == pytest.approx(1.6e-10)
    assert c.logzsol == pytest.approx(-0.3)

    # ``inside`` filter must exclude None-valued clumps under either polarity.
    assert catalog.filter_clumps(inside=True) == []
    assert catalog.filter_clumps(inside=False) == []
