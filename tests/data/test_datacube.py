"""Tests for FITS file handler."""

import numpy as np
import pytest

# Data check imports.
from jellyscope.data.data_store import DataStore
from jellyscope.data.model.datacube import DataCube


@pytest.mark.usefixtures("store")
class TestDatacube:
    """Tests for the DataCube class."""

    @pytest.fixture(autouse=True)
    def setup(self, store: DataStore):
        self.store: DataStore = store
        self.ds = store.get_dataset("A2744_F1228")
        self.dc: DataCube = self.ds.get_datacube("nircam")

    def test_datacube_loads_shape(self):
        assert self.dc.shape == (20, 221, 172)
        assert self.dc.n_channels == 20
        assert self.dc.ny == 221
        assert self.dc.nx == 172

    def test_filter_names_from_header(self):
        assert self.dc.filter_names[0] == "F070W"
        assert self.dc.filter_names[-1] == "F480M"
        assert len(self.dc.filter_names) == 20

    def test_get_slice_by_channel_index(self):
        s: np.ndarray = self.dc.get_slice_by_channel_index(0)
        assert s.shape == (221, 172)
        assert s.dtype == np.float64

    def test_both_datacubes_available(self):
        assert "nircam" in self.ds.list_datacubes()
        assert "nircam_matched" in self.ds.list_datacubes()

    def test_get_slice_out_of_range(self):
        with pytest.raises(IndexError, match="out of range"):
            self.dc.get_slice_by_channel_index(99)

    def test_fallback_filter_names(self):
        # Remove a filter key and test the fallback.
        filter_to_delete: str = "FILTER1"
        original_filter = self.dc.header.get(filter_to_delete)
        del self.dc.header[filter_to_delete]
        names: list[str] = self.dc._read_filter_names()
        assert names[0] == "CH1"
        assert names[1] == self.dc.filter_names[1]
        self.dc.header[filter_to_delete] = original_filter

    def test_spatial_shape(self):
        assert self.dc.spatial_shape == (221, 172)

    def test_get_datacube_unknown_name(self):
        with pytest.raises(KeyError, match="Unknown datacube"):
            self.ds.get_datacube("nonexistent")

    def test_get_datacubes_returns_dict(self):
        cubes = self.ds.datacubes
        assert isinstance(cubes, dict)
        assert "nircam" in cubes
        assert "nircam_matched" in cubes

    def test_datastore_singleton_default_config(self):
        DataStore.reset()
        try:
            instance = DataStore.get()
            assert isinstance(instance, DataStore)
        finally:
            DataStore.reset()
