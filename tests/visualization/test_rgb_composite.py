"""Tests for the Lupton RGB composite algorithm."""

import numpy as np

from jellyscope.visualization.rgb_composite import lupton_rgb_composite


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
