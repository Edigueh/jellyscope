"""Shared visualization helpers: dark-theme colors and axis layout.

Private to the visualization package — dedupes the layout dict shared between
the heatmap and RGB figure builders.
"""

from astropy.wcs import WCS

from jellyscope.data.model.coordinates import (
    ImageAxisBounds,
    pixel_scale_arcsec,
    wcs_affine_params,
)
from jellyscope.model.plotly import (
    Axis,
    Font,
    ImageBoundsMeta,
    Layout,
    LayoutMeta,
    Margin,
    Title,
    WcsAffineMeta,
)

# Shared dark-theme colors used by both image_viewer and rgb_composite layouts.
GRAY: str = "#cccccc"
DARK_GRAY: str = "#999"
SOFT_BLACK: str = "#333"
DARK_BLUE: str = "#1a1a2e"
SOFT_DARK_BLUE: str = "#16213e"


def _wcs_affine_meta(wcs: WCS | None, nx: int, ny: int) -> WcsAffineMeta | None:
    """Build the layout WCS meta for client-side hover RA/Dec, or None.

    Combines the linear pixel→RA/Dec params with the arcsec pixel scale and
    image-center pixel so the frontend can map an arcsec hover coord to RA/Dec.
    """
    params = wcs_affine_params(wcs) if wcs is not None else None
    if params is None:
        return None
    return WcsAffineMeta(
        crpix=params.crpix,
        crval=params.crval,
        scale=params.scale,
        cos_dec=params.cos_dec,
        arcsec_per_pix=pixel_scale_arcsec(wcs),
        cx=(nx - 1) / 2.0,
        cy=(ny - 1) / 2.0,
    )


def build_dark_axis_layout(
    *,
    title_text: str,
    axis_label_x: str,
    axis_label_y: str,
    bounds: ImageAxisBounds,
    wcs: WCS | None = None,
    nx: int,
    ny: int,
) -> Layout:
    """Return the dark-theme figure layout (xaxis/yaxis/bg/font/margin/dragmode/meta).

    ``wcs``/``nx``/``ny`` populate ``meta.wcs`` for client-side hover RA/Dec.
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
            ),
            wcs=_wcs_affine_meta(wcs, nx, ny),
        ),
    )
