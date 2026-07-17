"""Tests for the RGB composite algorithms."""

import base64
import io

import numpy as np
import pytest
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

    def _build(self, store: DataStore, method: str = "percentile_asinh"):
        dataset_name = store.list_datasets()[0]
        dataset = store.get_dataset(dataset_name)
        datacube_name = dataset.list_datacubes()[0]
        datacube = dataset.get_datacube(datacube_name)
        clumps = dataset.clumps
        assert clumps is not None
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
        d0 = fig.data[0]
        assert d0.type == "heatmap"
        assert d0.opacity == 0
        assert d0.showscale is False

    def test_click_target_has_no_customdata_grid(self, store: DataStore):
        """RA/Dec grid removed from the click target — was the payload cost."""
        fig = self._build(store)
        assert fig.data[0].customdata is None

    def test_meta_wcs_present_for_celestial(self, store: DataStore):
        fig = self._build(store)
        dataset = store.get_dataset(store.list_datasets()[0])
        dc = dataset.get_datacube(dataset.list_datacubes()[0])
        if not (dc.wcs is not None and dc.wcs.has_celestial):
            pytest.skip("fixture cube has no celestial WCS")
        assert fig.layout.meta.wcs is not None

    def test_layout_images_png_annotation(self, store: DataStore):
        fig = self._build(store)
        images = fig.layout.images
        assert len(images) == 1
        img = images[0]
        assert img.xref == "x"
        assert img.yref == "y"
        assert img.sizing == "stretch"
        # Image is centered on (0, 0) in arcsec offsets.
        assert img.x < 0
        assert img.y < 0
        assert img.source.startswith("data:image/png;base64,")

    def test_no_yaxis_autorange_reversed(self, store: DataStore):
        fig = self._build(store)
        # autorange is bool now; reversed mode would have been a special string.
        assert fig.layout.yaxis.autorange is False

    def test_png_dimensions_match_datacube(self, store: DataStore):
        from jellyscope.data.model.coordinates import pixel_scale_arcsec

        fig = self._build(store)
        dataset = store.get_dataset(store.list_datasets()[0])
        datacube = dataset.get_datacube(dataset.list_datacubes()[0])
        ny, nx = datacube.spatial_shape
        sec_pix = pixel_scale_arcsec(datacube.wcs)
        img = fig.layout.images[0]
        assert img.sizex == pytest.approx(nx * sec_pix, rel=1e-9)
        assert img.sizey == pytest.approx(ny * sec_pix, rel=1e-9)
        # Decode PNG and confirm dimensions still match the source pixel grid.
        b64 = img.source.removeprefix("data:image/png;base64,")
        png_bytes = base64.b64decode(b64)
        png = PILImage.open(io.BytesIO(png_bytes))
        assert png.size == (nx, ny)

    def test_centroid_y_is_arcsec_offset(self, store: DataStore):
        """Centroid y must equal (y0 - (ny-1)/2) * arcsec_per_pix."""
        from jellyscope.data.model.coordinates import pixel_scale_arcsec

        fig = self._build(store)
        clumps = store.get_dataset(store.list_datasets()[0]).clumps
        assert clumps is not None
        dataset = store.get_dataset(store.list_datasets()[0])
        datacube = dataset.get_datacube(dataset.list_datacubes()[0])
        clump_list = clumps.list_clumps()
        if not clump_list:
            return
        ny, _ = datacube.spatial_shape
        sec_pix = pixel_scale_arcsec(datacube.wcs)
        cy = (ny - 1) / 2.0
        centroids = fig.data[-1]
        expected_ys = [(c.y0 - cy) * sec_pix for c in clump_list]
        for got, exp in zip(centroids.y, expected_ys, strict=True):
            assert got == pytest.approx(exp, rel=1e-9, abs=1e-12)

    def test_data_order_preserves_clickable_first(self, store: DataStore):
        """app.js relies on data[0] being the click target; centroids are last."""
        fig = self._build(store)
        assert fig.data[0].type == "heatmap"
        # Last trace must be the centroid scatter so fig.data.pop() in JS toggles it.
        assert fig.data[-1].name == "Centroids"

    def test_lupton_method_path(self, store: DataStore):
        fig = self._build(store, method="lupton")
        assert fig.data[0].type == "heatmap"
        assert fig.layout.images[0].source.startswith("data:image/png;base64,")

    def test_image_yanchor_bottom(self, store: DataStore):
        """Image bottom must anchor at y=0 so it occupies y∈[0, ny] with overlays."""
        fig = self._build(store)
        img = fig.layout.images[0]
        assert img.yanchor == "bottom"

    def test_axes_locked_to_image_extent(self, store: DataStore):
        from jellyscope.data.model.coordinates import (
            image_axis_bounds,
            pixel_scale_arcsec,
        )

        fig = self._build(store)
        dataset = store.get_dataset(store.list_datasets()[0])
        datacube = dataset.get_datacube(dataset.list_datacubes()[0])
        ny, nx = datacube.spatial_shape
        sec = pixel_scale_arcsec(datacube.wcs) if datacube.wcs.has_celestial else None
        bounds = image_axis_bounds(nx, ny, sec)

        x = fig.layout.xaxis
        y = fig.layout.yaxis
        assert x.autorange is False
        assert y.autorange is False
        assert x.range == bounds.x
        assert y.range == bounds.y
        assert x.minallowed == bounds.x[0]
        assert x.maxallowed == bounds.x[1]
        assert y.minallowed == bounds.y[0]
        assert y.maxallowed == bounds.y[1]

    def test_meta_image_bounds_min_span(self, store: DataStore):
        from jellyscope.data.model.coordinates import (
            image_axis_bounds,
            pixel_scale_arcsec,
        )

        fig = self._build(store)
        dataset = store.get_dataset(store.list_datasets()[0])
        datacube = dataset.get_datacube(dataset.list_datacubes()[0])
        ny, nx = datacube.spatial_shape
        sec = pixel_scale_arcsec(datacube.wcs) if datacube.wcs.has_celestial else None
        bounds = image_axis_bounds(nx, ny, sec)

        ib = fig.layout.meta.imageBounds
        assert ib.x_min_span == bounds.x_min_span
        assert ib.y_min_span == bounds.y_min_span
