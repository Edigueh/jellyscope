"""Shared visualization helpers: dark-theme colors, customdata grid, axis layout.

Private to the visualization package — kept here to dedupe the per-cell
RA/Dec customdata loop and the layout dict shared between the heatmap and
RGB figure builders.
"""

import numpy as np
from astropy.wcs import WCS

from jellyscope.data.model.coordinates import (
    ImageAxisBounds,
    pixel_to_skycoord,
)
from jellyscope.model.plotly import (
    Axis,
    Font,
    HoverTemplate,
    ImageBoundsMeta,
    Layout,
    LayoutMeta,
    Margin,
    Title,
)

# Shared dark-theme colors used by both image_viewer and rgb_composite layouts.
GRAY: str = "#cccccc"
DARK_GRAY: str = "#999"
SOFT_BLACK: str = "#333"
DARK_BLUE: str = "#1a1a2e"
SOFT_DARK_BLUE: str = "#16213e"


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

    # Build (ny, nx, 4) object grid; non-finite ra/dec become None.
    grid = np.empty((ny, nx, 4), dtype=object)
    grid[..., 0] = xx_pix.astype(np.int64)
    grid[..., 1] = yy_pix.astype(np.int64)
    ra_obj = ra.astype(object)
    dec_obj = dec.astype(object)
    ra_obj[~np.isfinite(ra)] = None
    dec_obj[~np.isfinite(dec)] = None
    grid[..., 2] = ra_obj
    grid[..., 3] = dec_obj
    result: list[list[list[float | int | None]]] = grid.tolist()
    return result


def build_dark_axis_layout(
    *,
    title_text: str,
    axis_label_x: str,
    axis_label_y: str,
    bounds: ImageAxisBounds,
) -> Layout:
    """Return the dark-theme figure layout (xaxis/yaxis/bg/font/margin/dragmode/meta).

    Caller appends ``layout.images`` for figures that overlay a PNG.
    """
    x_min, x_max = bounds.x
    y_min, y_max = bounds.y
    return Layout(
        title=Title(text=title_text, font=Font(color=GRAY)),
        xaxis=Axis(
            title=axis_label_x,
            gridcolor=SOFT_BLACK,
            color=DARK_GRAY,
            range=(x_min, x_max),
            minallowed=x_min,
            maxallowed=x_max,
            autorange=False,
        ),
        yaxis=Axis(
            title=axis_label_y,
            gridcolor=SOFT_BLACK,
            color=DARK_GRAY,
            range=(y_min, y_max),
            minallowed=y_min,
            maxallowed=y_max,
            autorange=False,
        ),
        plot_bgcolor=DARK_BLUE,
        paper_bgcolor=SOFT_DARK_BLUE,
        font=Font(color=GRAY),
        margin=Margin(l=50, r=20, t=40, b=50),
        dragmode="pan",
        meta=LayoutMeta(
            imageBounds=ImageBoundsMeta(
                x_min_span=bounds.x_min_span,
                y_min_span=bounds.y_min_span,
            )
        ),
    )


def radec_hover(suffix: str) -> HoverTemplate:
    """Build the RA/Dec hover prefix + caller-supplied suffix.

    Heatmap appends ``"flux: %{z:.4f}<extra></extra>"``; RGB click target
    appends ``"<extra></extra>"``.
    """
    return HoverTemplate.radec_prefix(suffix)
