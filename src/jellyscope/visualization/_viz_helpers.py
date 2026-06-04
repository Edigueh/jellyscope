"""Shared visualization helpers: dark-theme colors, customdata grid, axis layout.

Private to the visualization package — kept here to dedupe the per-cell
RA/Dec customdata loop and the layout dict shared between the heatmap and
RGB figure builders.
"""

from typing import Any

import numpy as np
from astropy.wcs import WCS

from jellyscope.data.model.coordinates import (
    ImageAxisBounds,
    pixel_to_skycoord,
)

# Shared dark-theme colors used by both image_viewer and rgb_composite layouts.
GRAY: str = "#cccccc"
DARK_GRAY: str = "#999"
SOFT_BLACK: str = "#333"
DARK_BLUE: str = "#1a1a2e"
SOFT_DARK_BLUE: str = "#16213e"

# Hover prefix shared by heatmap and RGB click-target traces. Heatmap appends
# "flux: %{z:.4f}<extra></extra>"; RGB appends "<extra></extra>".
RADEC_HOVER_PREFIX: str = (
    "pix: (%{customdata[0]:d}, %{customdata[1]:d})<br>"
    'sky: (%{x:.3f}", %{y:.3f}")<br>'
    "RA: %{customdata[2]:.6f}°<br>"
    "Dec: %{customdata[3]:.6f}°<br>"
)


def build_radec_customdata_grid(
    nx: int, ny: int, wcs: WCS
) -> list[list[list[float | int | None]]]:
    """Per-cell ``[i, j, ra_deg|None, dec_deg|None]`` grid; shape ``(ny, nx, 4)``.

    Vectorizes ``pixel_to_skycoord`` over a meshgrid and returns Python lists so
    non-finite values serialize as JSON ``null``.
    """
    xx_pix, yy_pix = np.meshgrid(np.arange(nx, dtype=np.float64), np.arange(ny, dtype=np.float64))
    try:
        sky = pixel_to_skycoord(xx_pix, yy_pix, wcs)
        ra = np.asarray(sky.ra.deg, dtype=np.float64)
        dec = np.asarray(sky.dec.deg, dtype=np.float64)
    except Exception:  # pragma: no cover - defensive
        ra = np.full((ny, nx), np.nan)
        dec = np.full((ny, nx), np.nan)

    customdata: list[list[list[float | int | None]]] = []
    for j in range(ny):
        row_cd: list[list[float | int | None]] = []
        for i in range(nx):
            r = ra[j, i]
            d = dec[j, i]
            row_cd.append(
                [
                    int(i),
                    int(j),
                    float(r) if np.isfinite(r) else None,
                    float(d) if np.isfinite(d) else None,
                ]
            )
        customdata.append(row_cd)
    return customdata


def build_dark_axis_layout(
    *,
    title_text: str,
    axis_label_x: str,
    axis_label_y: str,
    bounds: ImageAxisBounds,
) -> dict[str, Any]:
    """Return the dark-theme figure layout (xaxis/yaxis/bg/font/margin/dragmode/meta).

    Caller appends ``layout["images"]`` for figures that overlay a PNG.
    """
    x_min, x_max = bounds["x"]
    y_min, y_max = bounds["y"]
    return {
        "title": {"text": title_text, "font": {"color": GRAY}},
        "xaxis": {
            "title": axis_label_x,
            "scaleanchor": "y",
            "constrain": "domain",
            "gridcolor": SOFT_BLACK,
            "color": DARK_GRAY,
            "range": [x_min, x_max],
            "minallowed": x_min,
            "maxallowed": x_max,
            "autorange": False,
        },
        "yaxis": {
            "title": axis_label_y,
            "gridcolor": SOFT_BLACK,
            "color": DARK_GRAY,
            "range": [y_min, y_max],
            "minallowed": y_min,
            "maxallowed": y_max,
            "autorange": False,
        },
        "plot_bgcolor": DARK_BLUE,
        "paper_bgcolor": SOFT_DARK_BLUE,
        "font": {"color": GRAY},
        "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
        "dragmode": "pan",
        "meta": {
            "imageBounds": {
                "x_min_span": bounds["x_min_span"],
                "y_min_span": bounds["y_min_span"],
            }
        },
    }
