"""Tests for the RGB composite algorithms."""

import numpy as np

from jellyscope.visualization.rgb_composite import (
    lupton_rgb_composite,
    percentile_asinh_composite,
)


class TestLuptonRGBComposite:
    def test_output_shape(self):
        rng = np.random.default_rng(42)
        r = rng.normal(100, 10, (30, 40))
        g = rng.normal(80, 10, (30, 40))
        b = rng.normal(60, 10, (30, 40))
        result = lupton_rgb_composite(r, g, b)
        assert result.shape == (30, 40, 3)
        assert result.dtype == np.uint8

    def test_output_range(self):
        rng = np.random.default_rng(42)
        r = rng.normal(100, 10, (20, 20))
        g = rng.normal(80, 10, (20, 20))
        b = rng.normal(60, 10, (20, 20))
        result = lupton_rgb_composite(r, g, b)
        assert np.all(result >= 0)
        assert np.all(result <= 255)

    def test_color_preservation(self):
        """A pixel where r=2*g=4*b should have R > G > B in output."""
        r = np.full((10, 10), 200.0)
        g = np.full((10, 10), 100.0)
        b = np.full((10, 10), 50.0)
        result = lupton_rgb_composite(r, g, b)
        # Center pixel should show R > G > B
        center = result[5, 5]
        assert center[0] >= center[1]  # R >= G
        assert center[1] >= center[2]  # G >= B

    def test_nan_becomes_black(self):
        r = np.full((10, 10), 100.0)
        g = np.full((10, 10), 80.0)
        b = np.full((10, 10), 60.0)
        r[3, 4] = np.nan
        result = lupton_rgb_composite(r, g, b)
        assert result[3, 4, 0] == 0
        assert result[3, 4, 1] == 0
        assert result[3, 4, 2] == 0

    def test_all_zero_becomes_black(self):
        r = np.zeros((10, 10))
        g = np.zeros((10, 10))
        b = np.zeros((10, 10))
        result = lupton_rgb_composite(r, g, b)
        assert np.all(result == 0)

    def test_all_nan_becomes_black(self):
        r = np.full((10, 10), np.nan)
        g = np.full((10, 10), np.nan)
        b = np.full((10, 10), np.nan)
        result = lupton_rgb_composite(r, g, b)
        assert np.all(result == 0)

    def test_custom_softening(self):
        rng = np.random.default_rng(7)
        r = rng.normal(100, 10, (20, 20))
        g = rng.normal(80, 10, (20, 20))
        b = rng.normal(60, 10, (20, 20))
        result_q4 = lupton_rgb_composite(r, g, b, softening=4.0)
        result_q16 = lupton_rgb_composite(r, g, b, softening=16.0)
        assert not np.array_equal(result_q4, result_q16)

    def test_bright_pixel_not_clipped_to_white(self):
        """Bright pixel should retain color, not burn to (255, 255, 255)."""
        r = np.full((10, 10), 50.0)
        g = np.full((10, 10), 50.0)
        b = np.full((10, 10), 50.0)
        # One very bright red pixel
        r[5, 5] = 5000.0
        g[5, 5] = 100.0
        b[5, 5] = 50.0
        result = lupton_rgb_composite(r, g, b)
        pixel = result[5, 5]
        # Should be dominantly red, NOT white
        assert pixel[0] > pixel[1]
        assert pixel[0] > pixel[2]


class TestPercentileAsinhComposite:
    def test_output_shape(self):
        rng = np.random.default_rng(42)
        r = rng.normal(100, 10, (30, 40))
        g = rng.normal(80, 10, (30, 40))
        b = rng.normal(60, 10, (30, 40))
        result = percentile_asinh_composite(r, g, b)
        assert result.shape == (30, 40, 3)
        assert result.dtype == np.uint8

    def test_output_range(self):
        rng = np.random.default_rng(7)
        r = rng.normal(100, 10, (20, 20))
        g = rng.normal(80, 10, (20, 20))
        b = rng.normal(60, 10, (20, 20))
        result = percentile_asinh_composite(r, g, b)
        assert np.all(result >= 0)
        assert np.all(result <= 255)

    def test_nan_becomes_black(self):
        rng = np.random.default_rng(1)
        r = rng.normal(100, 10, (10, 10))
        g = rng.normal(80, 10, (10, 10))
        b = rng.normal(60, 10, (10, 10))
        r[3, 4] = np.nan
        result = percentile_asinh_composite(r, g, b)
        assert result[3, 4, 0] == 0
        assert result[3, 4, 1] == 0
        assert result[3, 4, 2] == 0

    def test_all_nan_becomes_black(self):
        r = np.full((10, 10), np.nan)
        g = np.full((10, 10), np.nan)
        b = np.full((10, 10), np.nan)
        result = percentile_asinh_composite(r, g, b)
        assert np.all(result == 0)

    def test_constant_image_below_floor_is_black(self):
        # A flat image after median-subtract becomes 0; after the floor cut it stays 0.
        r = np.full((10, 10), 5.0)
        g = np.full((10, 10), 5.0)
        b = np.full((10, 10), 5.0)
        result = percentile_asinh_composite(r, g, b)
        assert np.all(result == 0)

    def test_bright_pixel_dominates(self):
        # Faint flat background plus a bright red pixel: that pixel should be the brightest.
        rng = np.random.default_rng(3)
        r = rng.normal(50, 1, (10, 10))
        g = rng.normal(50, 1, (10, 10))
        b = rng.normal(50, 1, (10, 10))
        r[5, 5] = 500.0
        result = percentile_asinh_composite(r, g, b)
        # Channel R at the bright pixel should hit (or be near) the max.
        assert result[5, 5, 0] == result[..., 0].max()

    def test_weights_scale_channels(self):
        rng = np.random.default_rng(11)
        r = rng.normal(100, 10, (15, 15))
        g = rng.normal(100, 10, (15, 15))
        b = rng.normal(100, 10, (15, 15))
        baseline = percentile_asinh_composite(r, g, b, weights=(1.0, 1.0, 1.0))
        boosted = percentile_asinh_composite(r, g, b, weights=(2.0, 1.0, 1.0))
        # Boosting R by 2x should not decrease the R channel anywhere.
        assert (boosted[..., 0] >= baseline[..., 0]).all()
