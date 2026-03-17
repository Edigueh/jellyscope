"""Tests for clump catalog."""


def test_clump_count(store):
    assert len(store.clumps.list_clumps()) == 23


def test_clump_properties(store):
    c = store.clumps.get_clump(0)
    assert c.clump_id == 0
    assert c.area_pix == 121
    assert c.component == "outside"
    assert c.inside is False


def test_pixel_mask(store):
    mask = store.clumps.get_pixel_mask(0)
    assert mask.shape == (221, 172)
    assert mask.dtype == bool
    assert mask.sum() == 121  # matches area_pix


def test_clump_at_pixel(store):
    # Clump 0 centroid is near (71.8, 19.9)
    cid = store.clumps.get_clump_at_pixel(72, 20)
    assert cid == 0


def test_no_clump_at_empty_pixel(store):
    cid = store.clumps.get_clump_at_pixel(0, 0)
    assert cid is None


def test_boundary_coords(store):
    boundary = store.clumps.get_boundary_coords(0)
    assert len(boundary) >= 3
    # Closed polygon: first == last
    assert boundary[0] == boundary[-1]


def test_filter_by_component(store):
    disk = store.clumps.filter_clumps(component="disk")
    outside = store.clumps.filter_clumps(component="outside")
    assert all(c.component == "disk" for c in disk)
    assert all(c.component == "outside" for c in outside)
    assert len(disk) + len(outside) == 23


def test_combined_mask(store):
    mask = store.clumps.get_combined_mask([0, 1])
    assert mask.sum() == 121 + 60  # area_pix of clump 0 + clump 1


def test_pixel_out_of_bounds(store):
    assert store.clumps.get_clump_at_pixel(-1, -1) is None
    assert store.clumps.get_clump_at_pixel(9999, 9999) is None


def test_boundary_cache_hit(store):
    b1 = store.clumps.get_boundary_coords(0)
    b2 = store.clumps.get_boundary_coords(0)
    assert b1 is b2


def test_small_clump_boundary(tmp_path):
    import pandas as pd

    from jellyscope.data.clumps import ClumpCatalog

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
    pixels_df = pd.DataFrame([{"clump_id": 99, "x": 5, "y": 5}, {"clump_id": 99, "x": 6, "y": 5}])
    props_df.to_csv(tmp_path / "props.csv", index=False)
    pixels_df.to_csv(tmp_path / "pixels.csv", index=False)

    catalog = ClumpCatalog(tmp_path / "props.csv", tmp_path / "pixels.csv", (10, 10))
    boundary = catalog.get_boundary_coords(99)
    assert len(boundary) >= 2
    assert boundary[0] == boundary[-1]


def test_qhull_error_fallback(store):
    from unittest.mock import patch

    from scipy.spatial import QhullError

    # Clear cache so we force recomputation
    store.clumps._boundaries.pop(0, None)
    with patch("jellyscope.data.clumps.ConvexHull", side_effect=QhullError("mock")):
        boundary = store.clumps.get_boundary_coords(0)
        assert len(boundary) >= 2
        assert boundary[0] == boundary[-1]


def test_filter_by_inside(store):
    inside = store.clumps.filter_clumps(inside=True)
    outside = store.clumps.filter_clumps(inside=False)
    assert all(c.inside is True for c in inside)
    assert all(c.inside is False for c in outside)
    assert len(inside) + len(outside) == 23


def test_to_properties_list(store):
    props = store.clumps.to_properties_list()
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
