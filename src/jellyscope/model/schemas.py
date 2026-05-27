"""Pydantic models for API request/response validation."""

from typing import Any

from pydantic import BaseModel

# --- Request models ---


class RectSelection(BaseModel):
    """Rectangle defined by two corners."""

    x0: int
    y0: int
    x1: int
    y1: int


class RegionRequest(BaseModel):
    """Request body for region spectrum extraction.

    Provide either a list of pixel coordinates or a rectangle, not both.
    """

    pixels: list[list[int]] | None = None
    rect: RectSelection | None = None


class CompareRequest(BaseModel):
    """Request body for multi-clump SED comparison."""

    clump_ids: list[int]


# --- Response models ---


class FilterInfo(BaseModel):
    """A single filter entry with index, name, and central wavelength."""

    index: int
    name: str
    wavelength: float


class ClumpListItem(BaseModel):
    """Summary of a clump for list display."""

    clump_id: int
    x0: float
    y0: float
    area_pix: int
    component: str
    inside: bool


class DatacubesResponse(BaseModel):
    """List of available datacube names."""

    datacubes: list[str]


class DatasetsResponse(BaseModel):
    """List of available dataset names plus the default selection."""

    datasets: list[str]
    default: str


class FiltersResponse(BaseModel):
    """List of filters for a datacube."""

    filters: list[FilterInfo]


class ViewerResponse(BaseModel):
    """Plotly figure for the galaxy viewer plus current filter name."""

    figure: dict[str, Any]
    filter_name: str


class ClumpsListResponse(BaseModel):
    """List of clumps with summary properties."""

    clumps: list[ClumpListItem]


class ClumpDetailResponse(BaseModel):
    """Full properties and boundary polygon for a single clump."""

    properties: dict[str, Any]
    boundary: list[list[float]]


class PixelClumpResponse(BaseModel):
    """Result of looking up which clump a pixel belongs to."""

    clump_id: int | None


class SpectrumResponse(BaseModel):
    """Spectrum data plus its Plotly figure."""

    spectrum: dict[str, Any]
    figure: dict[str, Any]


class CompareResponse(BaseModel):
    """Multi-clump comparison: overlaid Plotly figure plus individual spectra."""

    figure: dict[str, Any]
    spectra: list[dict[str, Any]]


class RGBViewerResponse(BaseModel):
    """Plotly figure for RGB composite viewer."""

    figure: dict[str, Any]
    r_filter: str
    g_filter: str
    b_filter: str
