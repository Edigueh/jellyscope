"""Tests for clump catalog."""

import numpy as np


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
