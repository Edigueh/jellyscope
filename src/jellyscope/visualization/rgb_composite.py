"""RGB color composite for JWST NIRCam imaging.

Two methods are provided:

- ``percentile_asinh_composite`` (default): per-band background subtraction,
  percentile clipping, asinh stretch, and pedestal cut. Not strictly color-preserving
  but produces clean, deep-field-style images.
- ``lupton_rgb_composite``: Lupton et al. (2004) Eq. 2 — color-preserving
  mapping where an object's RGB color depends only on its flux ratios.
"""

import base64
import io
from typing import Any, Literal

import numpy as np
from PIL import Image as PILImage

from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog
from jellyscope.data.model.coordinates import (
    arcsec_axis,
    image_arcsec_extent,
    image_axis_bounds,
    pixel_scale_arcsec,
)
from jellyscope.visualization._viz_helpers import (
    RADEC_HOVER_PREFIX,
    build_dark_axis_layout,
    build_radec_customdata_grid,
)
from jellyscope.visualization.image_viewer import (
    _default_alpha,
    _estimate_background,
    create_centroid_markers,
    create_clump_boundary_traces,
)

RGBMethod = Literal["percentile_asinh", "lupton"]


def lupton_rgb_composite(
    r_data: np.ndarray,
    g_data: np.ndarray,
    b_data: np.ndarray,
    softening: float = 8.0,
    alpha: float | None = None,
) -> np.ndarray:
    """Create an RGB composite using Lupton et al. (2004) Eq. 2.

    Apply the stretch to the total intensity I, then scale
    each band by f(I)/I. This preserves color regardless of brightness.

    Args:
        r_data, g_data, b_data: 2D flux arrays (ny, nx) for each band.
        softening: Q parameter controlling linear-to-log transition. Typical: 8-9.
        alpha: Linear stretch factor. If None, auto-estimated from background noise.

    Returns:
        uint8 array of shape (ny, nx, 3) suitable for Plotly go.Image.
    """
    intensity = (r_data + g_data + b_data) / 3.0
    m, sigma = _estimate_background(intensity)
    if alpha is None:
        alpha = _default_alpha(sigma)

    i_shifted = intensity - m
    f_i = np.arcsinh(alpha * softening * i_shifted) / softening

    # ratio = f(I) / (I - m) — the color-preserving scale factor
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(i_shifted > 0, f_i / i_shifted, 0.0)

    r_out = (r_data - m) * ratio
    g_out = (g_data - m) * ratio
    b_out = (b_data - m) * ratio

    r_out = np.maximum(r_out, 0.0)
    g_out = np.maximum(g_out, 0.0)
    b_out = np.maximum(b_out, 0.0)

    # Per-pixel normalization: if max(R,G,B) > 1, scale down to preserve color
    max_rgb = np.maximum(np.maximum(r_out, g_out), b_out)
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(max_rgb > 1.0, 1.0 / max_rgb, 1.0)
    r_out *= scale
    g_out *= scale
    b_out *= scale

    # NaN handling: pixels invalid in any band become black
    nan_mask = ~(np.isfinite(r_data) & np.isfinite(g_data) & np.isfinite(b_data))
    r_out[nan_mask] = 0.0
    g_out[nan_mask] = 0.0
    b_out[nan_mask] = 0.0

    # Global normalization to [0, 1] using 99.5th percentile
    rgb = np.stack([r_out, g_out, b_out], axis=-1)
    positive = rgb[rgb > 0]
    vmax = float(np.percentile(positive, 99.5)) if positive.size > 0 else 1.0
    if vmax > 0:
        rgb = rgb / vmax
    rgb = np.clip(rgb, 0.0, 1.0)

    return (rgb * 255).astype(np.uint8)


def _normalize_band_asinh(
    band: np.ndarray,
    pmin: float,
    pmax: float,
    scale: float,
    floor: float,
) -> np.ndarray:
    """Per-band normalization: median subtract, percentile clip, asinh, floor."""
    finite = band[np.isfinite(band)]
    if finite.size == 0:
        return np.zeros_like(band, dtype=np.float64)

    bkg = float(np.median(finite))
    x = band - bkg

    finite_x = x[np.isfinite(x)]
    lo = float(np.percentile(finite_x, pmin))
    hi = float(np.percentile(finite_x, pmax))
    denom = hi - lo if hi > lo else 1.0
    y = (x - lo) / denom
    y = np.clip(y, 0.0, 1.0)

    y = np.arcsinh(y / scale) / np.arcsinh(1.0 / scale)
    y = np.where(y < floor, 0.0, y)
    y = np.clip(y, 0.0, 1.0)
    return y


def percentile_asinh_composite(
    r_data: np.ndarray,
    g_data: np.ndarray,
    b_data: np.ndarray,
    pmin: float = 10.0,
    pmax: float = 99.9,
    scale: float = 0.1,
    floor: float = 0.05,
    weights: tuple[float, float, float] = (1.0, 1.02, 1.02),
) -> np.ndarray:
    """Per-band percentile + asinh stretch composite (Andressa's recipe).

    Each band is independently background-subtracted (median), percentile-clipped,
    asinh-stretched, and pedestal-cut, then weighted.

    Args:
        r_data, g_data, b_data: 2D flux arrays.
        pmin, pmax: Percentile bounds for the linear clip step (in percent).
        scale: asinh softening parameter — smaller boosts faint features more.
        floor: pedestal cut applied after stretch; pixels below become 0.
        weights: (wR, wG, wB) per-channel multipliers applied at the end.

    Returns:
        uint8 array (ny, nx, 3) suitable for Plotly go.Image.
    """
    r = _normalize_band_asinh(r_data, pmin, pmax, scale, floor) * weights[0]
    g = _normalize_band_asinh(g_data, pmin, pmax, scale, floor) * weights[1]
    b = _normalize_band_asinh(b_data, pmin, pmax, scale, floor) * weights[2]

    nan_mask = ~(np.isfinite(r_data) & np.isfinite(g_data) & np.isfinite(b_data))
    r[nan_mask] = 0.0
    g[nan_mask] = 0.0
    b[nan_mask] = 0.0

    rgb = np.stack([r, g, b], axis=-1)
    rgb = np.clip(rgb, 0.0, 1.0)
    return (rgb * 255).astype(np.uint8)


def _rgb_to_png_data_url(rgb: np.ndarray) -> str:
    """Encode RGB uint8 array to base64 PNG.

    flipud applied here so the PNG, when placed on a Cartesian y-up axis with
    y=0, sizey=ny, has FITS row j at axis y=j.
    """
    flipped = np.flipud(rgb)
    img = PILImage.fromarray(flipped, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_rgb_figure(
    datacube: DataCube,
    r_index: int,
    g_index: int,
    b_index: int,
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    method: RGBMethod = "percentile_asinh",
    softening: float = 8.0,
    alpha: float | None = None,
) -> dict[str, Any]:
    """Build a Plotly figure with RGB composite + clump overlays.

    Pixels are rendered via ``layout.images[]`` (PNG annotation) on a Cartesian
    axis. An invisible ``go.Heatmap`` carries clicks so ``point.y`` arrives at
    the backend in raw FITS array space.

    Args:
        method: ``"percentile_asinh"`` (default) or ``"lupton"``.
        softening: Lupton ``Q`` parameter (only used when ``method='lupton'``).
        alpha: Lupton linear stretch factor (only used when ``method='lupton'``).
    """
    r_data = datacube.get_slice_by_channel_index(r_index)
    g_data = datacube.get_slice_by_channel_index(g_index)
    b_data = datacube.get_slice_by_channel_index(b_index)

    if method == "lupton":
        rgb = lupton_rgb_composite(r_data, g_data, b_data, softening, alpha)
    else:
        rgb = percentile_asinh_composite(r_data, g_data, b_data)

    ny, nx = rgb.shape[:2]
    has_sky = datacube.wcs is not None and datacube.wcs.has_celestial
    sec_pix: float | None = pixel_scale_arcsec(datacube.wcs) if has_sky else None

    click_target: dict[str, Any] = {
        "type": "heatmap",
        "z": np.zeros((ny, nx)).tolist(),
        "showscale": False,
        "opacity": 0,
        "colorscale": [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
    }

    if has_sky and sec_pix is not None:
        click_target["x"] = arcsec_axis(nx, sec_pix).tolist()
        click_target["y"] = arcsec_axis(ny, sec_pix).tolist()
        click_target["customdata"] = build_radec_customdata_grid(nx, ny, datacube.wcs)
        click_target["hovertemplate"] = RADEC_HOVER_PREFIX + "<extra></extra>"
    else:
        click_target["hoverinfo"] = "skip"

    boundaries = create_clump_boundary_traces(clumps, selected_ids, wcs=datacube.wcs)
    centroids = create_centroid_markers(clumps, has_sky=has_sky, sec_pix=sec_pix or 0.0)

    data: list[dict[str, Any]] = [click_target, *boundaries, centroids]

    r_name = datacube.filter_names[r_index]
    g_name = datacube.filter_names[g_index]
    b_name = datacube.filter_names[b_index]

    if has_sky and sec_pix is not None:
        extent = image_arcsec_extent(nx, ny, sec_pix)
        axis_label_x = "x offset (arcsec)"
        axis_label_y = "y offset (arcsec)"
    else:
        extent = {"x": 0, "y": 0, "sizex": nx, "sizey": ny}
        axis_label_x = "x (pixels)"
        axis_label_y = "y (pixels)"

    bounds = image_axis_bounds(nx, ny, sec_pix)

    layout: dict[str, Any] = build_dark_axis_layout(
        title_text=f"RGB: {r_name} / {g_name} / {b_name}",
        axis_label_x=axis_label_x,
        axis_label_y=axis_label_y,
        bounds=bounds,
    )
    layout["images"] = [
        {
            "source": _rgb_to_png_data_url(rgb),
            "xref": "x",
            "yref": "y",
            "x": extent["x"],
            "y": extent["y"],
            "yanchor": "bottom",
            "sizex": extent["sizex"],
            "sizey": extent["sizey"],
            "sizing": "stretch",
            "layer": "below",
        }
    ]

    return {"data": data, "layout": layout}
