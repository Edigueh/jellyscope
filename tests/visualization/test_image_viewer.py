"""Tests for the Lupton asinh stretch and background estimation."""

import numpy as np

from jellyscope.visualization.image_viewer import (
    _estimate_background,
    _lupton_asinh_stretch,
    _normalize_stretch,
)


class TestEstimateBackground:
    def test_gaussian_noise(self):
        rng = np.random.default_rng(42)
        data = rng.normal(loc=100.0, scale=5.0, size=(100, 100))
        median, std = _estimate_background(data)
        assert abs(median - 100.0) < 1.0
        assert abs(std - 5.0) < 1.0

    def test_all_nan_returns_defaults(self):
        data = np.full((10, 10), np.nan)
        median, std = _estimate_background(data)
        assert median == 0.0
        assert std == 1.0

    def test_empty_array(self):
        data = np.array([])
        median, std = _estimate_background(data)
        assert median == 0.0
        assert std == 1.0


class TestLuptonAsinhStretch:
    def test_basic_output_range(self):
        rng = np.random.default_rng(42)
        data = rng.normal(loc=50.0, scale=10.0, size=(50, 50))
        result = _lupton_asinh_stretch(data)
        assert result.shape == (50, 50)
        finite = result[np.isfinite(result)]
        assert np.all(finite >= 0.0)
        assert np.all(finite <= 1.0)

    def test_nan_preserved(self):
        data = np.array([[1.0, 2.0, np.nan], [4.0, np.nan, 6.0]])
        result = _lupton_asinh_stretch(data)
        assert np.isnan(result[0, 2])
        assert np.isnan(result[1, 1])
        assert not np.isnan(result[0, 0])

    def test_all_nan_returns_zeros(self):
        data = np.full((10, 10), np.nan)
        result = _lupton_asinh_stretch(data)
        assert np.all(result == 0.0)

    def test_uniform_array(self):
        data = np.full((20, 20), 42.0)
        result = _lupton_asinh_stretch(data)
        # Uniform => background == data, so (data - m) ~ 0 => stretched ~ 0
        finite = result[np.isfinite(result)]
        assert np.all(finite >= 0.0)
        assert np.all(finite <= 1.0)

    def test_custom_softening_parameter(self):
        rng = np.random.default_rng(7)
        data = rng.normal(loc=100.0, scale=10.0, size=(30, 30))
        result_q4 = _lupton_asinh_stretch(data, softening=4.0)
        result_q16 = _lupton_asinh_stretch(data, softening=16.0)
        # Different Q should produce different results
        assert not np.allclose(result_q4, result_q16)

    def test_custom_alpha_parameter(self):
        rng = np.random.default_rng(7)
        data = rng.normal(loc=100.0, scale=10.0, size=(30, 30))
        result_a1 = _lupton_asinh_stretch(data, alpha=0.001)
        result_a2 = _lupton_asinh_stretch(data, alpha=0.01)
        assert not np.allclose(result_a1, result_a2)


class TestNormalizeStretchDispatch:
    def test_dispatch_log(self):
        data = np.array([[1.0, 10.0], [100.0, 1000.0]])
        result = _normalize_stretch(data, stretch="log")
        assert result.shape == (2, 2)

    def test_dispatch_lupton_asinh(self):
        rng = np.random.default_rng(0)
        data = rng.normal(50, 10, (20, 20))
        result = _normalize_stretch(data, stretch="lupton_asinh")
        finite = result[np.isfinite(result)]
        assert np.all(finite >= 0.0)
        assert np.all(finite <= 1.0)

    def test_dispatch_power(self):
        rng = np.random.default_rng(0)
        data = rng.normal(50, 10, (20, 20))
        result = _normalize_stretch(data, stretch="power")
        assert result.shape == (20, 20)

    def test_dispatch_unknown_falls_back_to_log(self):
        data = np.array([[1.0, 10.0], [100.0, 1000.0]])
        result_unknown = _normalize_stretch(data, stretch="unknown_stretch")
        result_log = _normalize_stretch(data, stretch="log")
        assert np.allclose(result_unknown, result_log, equal_nan=True)

    def test_default_is_log(self):
        data = np.array([[1.0, 10.0], [100.0, 1000.0]])
        result_default = _normalize_stretch(data)
        result_log = _normalize_stretch(data, stretch="log")
        assert np.allclose(result_default, result_log, equal_nan=True)
