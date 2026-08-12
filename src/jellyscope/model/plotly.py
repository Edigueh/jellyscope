"""Strict Pydantic models for the subset of Plotly's schema this app emits.

Each model is ``extra="forbid"`` so a typo or stray field fails loudly at
construction time. Adding a Plotly attribute we want to set requires editing
this file — the explicit catalog is the point.

JSON wire format matches Plotly.js: ``model.model_dump(mode="json",
exclude_none=True)`` (or FastAPI's response serialization, which does the
same) produces the dicts ``Plotly.newPlot`` expects.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ColorScale = str | list[list[float | str]]
"""Plotly accepts a named colorscale (e.g. ``"Viridis"``) or an explicit
``[[stop, color], ...]`` list."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- leaf models ---


class Font(_Strict):
    color: str | None = None
    size: int | None = None


class Title(_Strict):
    text: str
    font: Font | None = None


class ColorBar(_Strict):
    title: str
    thickness: int


class Line(_Strict):
    color: str
    width: float


class Marker(_Strict):
    color: str
    size: int
    symbol: str


class Axis(_Strict):
    title: str
    gridcolor: str
    color: str
    range: tuple[float, float]
    minallowed: float
    maxallowed: float
    autorange: bool


class Margin(_Strict):
    # Plotly uses single-letter keys; ruff E741 is for "l" as variable, not field.
    l: int  # noqa: E741
    r: int
    t: int
    b: int


class LayoutImage(_Strict):
    source: str
    xref: Literal["x"]
    yref: Literal["y"]
    x: float
    y: float
    yanchor: Literal["bottom"]
    sizex: float
    sizey: float
    sizing: Literal["stretch"]
    layer: Literal["below"]


class ImageBoundsMeta(_Strict):
    x_min_span: float
    y_min_span: float
    # Data extents (axis units) so the frontend can size the plot box to the
    # data aspect ratio (square pixels) without a Plotly scaleanchor lock.
    x_range: tuple[float, float]
    y_range: tuple[float, float]


class WcsAffineMeta(_Strict):
    """Compact linear pixel↔RA/Dec transform for client-side hover readout.

    These cut datacubes have an axis-aligned, rotation-free WCS (diagonal PC,
    no CD/SIP), so RA/Dec is affine in pixel coords to ~16 mas over the cut —
    ample for a hover tooltip. The frontend reconstructs RA/Dec from the arcsec
    hover coordinate instead of the backend shipping a per-pixel grid.
    """

    crpix: tuple[float, float]  # 0-based reference pixel (x, y)
    crval: tuple[float, float]  # reference world coords (ra_deg, dec_deg)
    scale: tuple[float, float]  # PC diagonal * cdelt (deg/pixel) for (x, y)
    cos_dec: float  # cos(crval_dec) — RA scaling near the reference
    arcsec_per_pix: float  # plot axes are arcsec-from-center; convert first
    cx: float  # image-center pixel x = (nx - 1) / 2
    cy: float  # image-center pixel y = (ny - 1) / 2


class LayoutMeta(_Strict):
    imageBounds: ImageBoundsMeta  # noqa: N815 — Plotly key is camelCase by convention
    wcs: WcsAffineMeta | None = None


class Layout(_Strict):
    title: Title
    xaxis: Axis
    yaxis: Axis
    plot_bgcolor: str
    paper_bgcolor: str
    font: Font
    margin: Margin
    dragmode: Literal["pan"]
    meta: LayoutMeta
    images: list[LayoutImage] = []


# --- traces (discriminated union on ``type``) ---


class HeatmapTrace(_Strict):
    type: Literal["heatmap"] = "heatmap"
    z: list[list[float | None]]
    colorscale: ColorScale
    hoverongaps: bool
    showscale: bool
    colorbar: ColorBar | None = None
    opacity: float | None = None
    x: list[float] | None = None
    y: list[float] | None = None
    customdata: list[list[list[float | int | None]]] | None = None
    hovertemplate: str | None = None
    hoverinfo: Literal["skip"] | None = None


class ScatterTrace(_Strict):
    type: Literal["scatter"] = "scatter"
    x: list[float]
    y: list[float]
    mode: Literal["lines", "markers+text"]
    line: Line | None = None
    marker: Marker | None = None
    name: str
    showlegend: bool
    customdata: list[list[float | None]] | None = None
    hovertemplate: str | None = None
    hoverinfo: Literal["text"] | None = None
    text: str | list[str] | None = None
    textposition: str | None = None
    textfont: Font | None = None


PlotlyTrace = Annotated[HeatmapTrace | ScatterTrace, Field(discriminator="type")]


class Figure(_Strict):
    data: list[PlotlyTrace]
    layout: Layout
