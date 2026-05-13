"""RGB color composite using the Lupton et al. (2004) algorithm.

Implements Equation 2 from the paper: color-preserving mapping that ensures
an object's color in the RGB image depends only on its flux ratios, not brightness.
"""

from typing import Any

import numpy as np

from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog
from jellyscope.visualization.image_viewer import (
    _estimate_background,
    create_centroid_markers,
    create_clump_boundary_traces,
)

_GRAY: str = "#cccccc"
_DARK_GRAY: str = "#999"
_SOFT_BLACK: str = "#333"
_DARK_BLUE: str = "#1a1a2e"
_SOFT_DARK_BLUE: str = "#16213e"


def lupton_rgb_composite(
    r_data: np.ndarray,
    g_data: np.ndarray,
    b_data: np.ndarray,
    softening: float = 8.0,
    alpha: float | None = None,
) -> np.ndarray:
    """Create an RGB composite using Lupton et al. (2004) Eq. 2.

    The key insight: apply the stretch to the total intensity I, then scale
    each band by f(I)/I. This preserves color regardless of brightness.

    Args:
        r_data, g_data, b_data: 2D flux arrays (ny, nx) for each band.
        softening: Q parameter controlling linear-to-log transition. Typical: 8-9.
        alpha: Linear stretch factor. If None, auto-estimated from background noise.

    Returns:
        uint8 array of shape (ny, nx, 3) suitable for Plotly go.Image.
    """
    # TODO: Arrumar a equação.
    # Não faz sentido ter os filtros daquela forma.
    # Limitar a escolha de filtros.
    # Deixar 3 filtros pro azul por exemplo.
    # Escolher os outros filtros a partir do primeiro.
    # A partir da primeira escolha, restringir as próximas opções.
    intensity = (r_data + g_data + b_data) / 3.0
    m, sigma = _estimate_background(intensity)
    if alpha is None:
        alpha = 0.02 / (sigma + 1e-10)

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


def build_rgb_figure(
    datacube: DataCube,
    r_index: int,
    g_index: int,
    b_index: int,
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    softening: float = 8.0,
    alpha: float | None = None,
) -> dict[str, Any]:
    """Build a Plotly figure with RGB composite + clump overlays."""
    r_data = datacube.get_slice_by_channel_index(r_index)
    g_data = datacube.get_slice_by_channel_index(g_index)
    b_data = datacube.get_slice_by_channel_index(b_index)

    rgb = lupton_rgb_composite(r_data, g_data, b_data, softening, alpha)
    ny = rgb.shape[0]
    rgb = np.flipud(rgb)

    image_trace: dict[str, Any] = {
        "type": "image",
        "z": rgb.tolist(),
    }

    boundaries = create_clump_boundary_traces(clumps, selected_ids)
    for trace in boundaries:
        trace["y"] = [ny - 1 - y for y in trace["y"]]
    centroids = create_centroid_markers(clumps)
    centroids["y"] = [ny - 1 - y for y in centroids["y"]]

    data: list[dict[str, Any]] = [image_trace, *boundaries, centroids]

    r_name = datacube.filter_names[r_index]
    g_name = datacube.filter_names[g_index]
    b_name = datacube.filter_names[b_index]

    layout: dict[str, Any] = {
        "title": {
            "text": f"RGB: {r_name} / {g_name} / {b_name}",
            "font": {"color": _GRAY},
        },
        "xaxis": {
            "title": "x (pixels)",
            "scaleanchor": "y",
            "constrain": "domain",
            "gridcolor": _SOFT_BLACK,
            "color": _DARK_GRAY,
        },
        "yaxis": {
            "title": "y (pixels)",
            "gridcolor": _SOFT_BLACK,
            "color": _DARK_GRAY,
            "autorange": "reversed",
        },
        "plot_bgcolor": _DARK_BLUE,
        "paper_bgcolor": _SOFT_DARK_BLUE,
        "font": {"color": _GRAY},
        "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
        "dragmode": "pan",
    }

    return {"data": data, "layout": layout}
