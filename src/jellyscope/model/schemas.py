"""Pydantic models for API request/response validation."""

from typing import Any

from pydantic import BaseModel

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
