"""Tests for the RGB composite algorithms."""

import base64
import io

import numpy as np
from PIL import Image as PILImage

from jellyscope.data.data_store import DataStore
from jellyscope.visualization.rgb_composite import (
    build_rgb_figure,
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


class TestBuildRGBFigure:
    """Figure assembly: invisible heatmap click target + layout.images PNG."""

    def _build(self, store: DataStore, method: str = "percentile_asinh") -> dict:
        dataset_name = store.list_datasets()[0]
        dataset = store.get_dataset(dataset_name)
        datacube_name = dataset.list_datacubes()[0]
        datacube = dataset.get_datacube(datacube_name)
        clumps = store.get_clumps(dataset_name)
        nchan = datacube.n_channels
        return build_rgb_figure(
            datacube,
            r_index=min(nchan - 1, 2),
            g_index=min(nchan - 1, 1),
            b_index=0,
            clumps=clumps,
            method=method,
        )

    def test_data0_is_invisible_heatmap(self, store: DataStore):
        fig = self._build(store)
        d0 = fig["data"][0]
        assert d0["type"] == "heatmap"
        assert d0["opacity"] == 0
        assert d0["showscale"] is False

    def test_layout_images_png_annotation(self, store: DataStore):
        fig = self._build(store)
        images = fig["layout"]["images"]
        assert len(images) == 1
        img = images[0]
        assert img["xref"] == "x"
        assert img["yref"] == "y"
        assert img["sizing"] == "stretch"
        assert img["x"] == 0
        assert img["y"] == 0
        assert img["source"].startswith("data:image/png;base64,")

    def test_no_yaxis_autorange_reversed(self, store: DataStore):
        fig = self._build(store)
        yaxis = fig["layout"]["yaxis"]
        assert yaxis.get("autorange") != "reversed"

    def test_png_dimensions_match_datacube(self, store: DataStore):
        fig = self._build(store)
        dataset = store.get_dataset(store.list_datasets()[0])
        datacube = dataset.get_datacube(dataset.list_datacubes()[0])
        ny, nx = datacube.spatial_shape
        img = fig["layout"]["images"][0]
        assert img["sizex"] == nx
        assert img["sizey"] == ny
        # Decode PNG and confirm dimensions.
        b64 = img["source"].removeprefix("data:image/png;base64,")
        png_bytes = base64.b64decode(b64)
        png = PILImage.open(io.BytesIO(png_bytes))
        assert png.size == (nx, ny)

    def test_centroid_y_is_raw_fits_y(self, store: DataStore):
        """Regression: triple-flip set centroid y to ny-1-y0. Ensure raw y0 is used."""
        fig = self._build(store)
        clumps = store.get_clumps(store.list_datasets()[0])
        clump_list = clumps.list_clumps()
        if not clump_list:
            return  # nothing to assert
        # Centroid trace is the last data entry.
        centroids = fig["data"][-1]
        # Expected y values are raw y0 from each clump, in catalog order.
        expected_ys = [c.y0 for c in clump_list]
        assert list(centroids["y"]) == expected_ys

    def test_data_order_preserves_clickable_first(self, store: DataStore):
        """app.js relies on data[0] being the click target; centroids are last."""
        fig = self._build(store)
        assert fig["data"][0]["type"] == "heatmap"
        # Last trace must be the centroid scatter so fig.data.pop() in JS toggles it.
        assert fig["data"][-1].get("name") == "Centroids"

    def test_lupton_method_path(self, store: DataStore):
        fig = self._build(store, method="lupton")
        assert fig["data"][0]["type"] == "heatmap"
        assert fig["layout"]["images"][0]["source"].startswith("data:image/png;base64,")

    def test_image_yanchor_bottom(self, store: DataStore):
        """Image bottom must anchor at y=0 so it occupies y∈[0, ny] with overlays."""
        fig = self._build(store)
        img = fig["layout"]["images"][0]
        assert img["yanchor"] == "bottom"
