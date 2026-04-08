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
        self.dc: DataCube = store.get_datacube("nircam")

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

    def test_get_slice_by_name(self):
        s: np.ndarray = self.dc.get_slice_by_name("F200W")
        assert s.shape == (221, 172)

    def test_get_spectrum_at_pixel(self):
        spec: np.ndarray = self.dc.get_spectrum_at_pixel(80, 100)
        assert spec.shape == (20,)

    def test_to_json_slice(self):
        json: list[list[int]] = self.dc.to_json_slice(0)
        assert len(json) == 221
        assert len(json)
        assert all(isinstance(v, float | type(None)) for v in json[0])

    def test_both_datacubes_available(self):
        assert "nircam" in self.store.list_datacubes()
        assert "nircam_matched" in self.store.list_datacubes()

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

    def test_get_slice_by_name_invalid(self):
        with pytest.raises(ValueError, match="NONEXISTENT"):
            self.dc.get_slice_by_name("NONEXISTENT")

    def test_get_mean_spectrum_for_mask(self):
        mask = np.zeros((self.dc.ny, self.dc.nx), dtype=bool)
        mask[100, 80] = True
        mask[110, 90] = True
        mean, std = self.dc.get_mean_spectrum_for_mask(mask)
        assert mean.shape == (self.dc.n_channels,)
        assert std.shape == (self.dc.n_channels,)
        assert np.all(np.isfinite(mean) | np.isnan(mean))

    def test_get_mean_spectrum_for_mask_all_true(self):
        mask = np.ones((self.dc.ny, self.dc.nx), dtype=bool)
        mean, _std = self.dc.get_mean_spectrum_for_mask(mask)
        expected_mean = np.nanmean(self.dc.data, axis=(1, 2))
        np.testing.assert_allclose(mean, expected_mean)

    def test_get_datacube_unknown_name(self):
        with pytest.raises(KeyError, match="Unknown datacube"):
            self.store.get_datacube("nonexistent")

    def test_get_datacubes_returns_dict(self):
        cubes = self.store.get_datacubes()
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
