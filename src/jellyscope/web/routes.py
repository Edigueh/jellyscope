"""REST API endpoints and page routes."""

from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import HTMLResponse, Response

from jellyscope.config import NIRCAM_WAVELENGTHS
from jellyscope.data.data_store import DataStore
from jellyscope.model.schemas import (
    ClumpDetailResponse,
    ClumpListItem,
    ClumpsListResponse,
    CompareRequest,
    CompareResponse,
    DatacubesResponse,
    FilterInfo,
    FiltersResponse,
    PixelClumpResponse,
    RegionRequest,
    RGBViewerResponse,
    SpectrumResponse,
    ViewerResponse,
)
from jellyscope.spec_analysis.spectral import (
    extract_clump_spectrum,
    extract_pixel_spectrum,
    extract_region_spectrum,
)
from jellyscope.visualization.image_viewer import build_viewer_figure
from jellyscope.visualization.properties_panel import format_clump_properties
from jellyscope.visualization.rgb_composite import build_rgb_figure
from jellyscope.visualization.spectrum_plot import create_multi_sed_figure, create_sed_figure

router = APIRouter()


def _store() -> DataStore:
    return DataStore.get()


# Pages.
@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> Response:
    store = _store()
    return request.app.state.templates.TemplateResponse(  # type: ignore[no-any-return]
        request,
        "index.html",
        {
            "datacubes": store.list_datacubes(),
            "filters": store.get_datacube("nircam").filter_names,
            "wavelengths": NIRCAM_WAVELENGTHS,
        },
    )


# Datacube info.
@router.get("/api/datacubes", response_model=DatacubesResponse)
def list_datacubes() -> DatacubesResponse:
    store = _store()
    return DatacubesResponse(datacubes=store.list_datacubes())


@router.get("/api/filters/{datacube_name}", response_model=FiltersResponse)
def list_filters(datacube_name: str) -> FiltersResponse:
    dc = _store().get_datacube(datacube_name)

    filters: list[FilterInfo] = []
    for i, name in enumerate(dc.filter_names):
        filters.append(
            FilterInfo(
                index=i,
                name=name,
                wavelength=NIRCAM_WAVELENGTHS.get(name, 0.0),
            )
        )
    return FiltersResponse(filters=filters)


# Image viewer.
@router.get("/api/viewer/{datacube_name}/rgb", response_model=RGBViewerResponse)
def get_rgb_viewer_figure(
    datacube_name: str,
    r: Annotated[int, Query(description="Red channel filter index")],
    g: Annotated[int, Query(description="Green channel filter index")],
    b: Annotated[int, Query(description="Blue channel filter index")],
    selected: Annotated[str, Query()] = "",
    softening: Annotated[float, Query()] = 8.0,
) -> RGBViewerResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)
    n_ch = dc.n_channels
    for label, idx in [("r", r), ("g", g), ("b", b)]:
        if not 0 <= idx < n_ch:
            raise HTTPException(
                status_code=400,
                detail=f"Channel index {label}={idx} out of range [0, {n_ch})",
            )
    selected_ids: list[int] = (
        [int(i) for i in selected.split(",") if i.strip()] if selected else []
    )
    figure: dict[str, Any] = build_rgb_figure(dc, r, g, b, store.clumps, selected_ids, softening)
    return RGBViewerResponse(
        figure=figure,
        r_filter=dc.filter_names[r],
        g_filter=dc.filter_names[g],
        b_filter=dc.filter_names[b],
    )


@router.get("/api/viewer/{datacube_name}/{channel_index}", response_model=ViewerResponse)
def get_viewer_figure(
    datacube_name: str,
    channel_index: int,
    selected: Annotated[str, Query()] = "",
    colorscale: Annotated[str, Query()] = "Viridis",
    stretch: Annotated[Literal["log", "lupton_asinh", "power"], Query()] = "log",
) -> ViewerResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)
    if not 0 <= channel_index < dc.n_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Channel index {channel_index} out of range [0, {dc.n_channels})",
        )
    selected_ids: list[int] = (
        [int(i) for i in selected.split(",") if i.strip()] if selected else []
    )
    figure: dict[str, Any] = build_viewer_figure(
        dc, channel_index, store.clumps, selected_ids, colorscale, stretch
    )
    return ViewerResponse(figure=figure, filter_name=dc.filter_names[channel_index])


# Clumps.
@router.get("/api/clumps", response_model=ClumpsListResponse)
def list_clumps(
    component: Annotated[str | None, Query()] = None,
    inside: Annotated[bool | None, Query()] = None,
) -> ClumpsListResponse:
    store = _store()
    clumps = store.clumps.filter_clumps(component, inside)
    return ClumpsListResponse(
        clumps=[
            ClumpListItem(
                clump_id=c.clump_id,
                x0=round(c.x0, 2),
                y0=round(c.y0, 2),
                area_pix=c.area_pix,
                component=c.component,
                inside=c.inside,
            )
            for c in clumps
        ]
    )


@router.get("/api/clumps/{clump_id}", response_model=ClumpDetailResponse)
def get_clump(clump_id: int) -> ClumpDetailResponse:
    store = _store()
    clump = store.clumps.get_clump_by_id(clump_id)
    boundary = store.clumps.get_boundary_coords(clump_id)
    props = format_clump_properties(clump)
    return ClumpDetailResponse(
        properties=props,
        boundary=[list(coord) for coord in boundary],
    )


@router.get("/api/clumps/{clump_id}/spectrum/{datacube_name}", response_model=SpectrumResponse)
def get_clump_spectrum(clump_id: int, datacube_name: str) -> SpectrumResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)
    spectrum = extract_clump_spectrum(dc, store.clumps, clump_id)
    figure = create_sed_figure(spectrum, f"Clump {clump_id} — SED")
    return SpectrumResponse(spectrum=spectrum, figure=figure)


# Pixel Interaction.
@router.get("/api/pixel/{x}/{y}/clump", response_model=PixelClumpResponse)
def get_pixel_clump(x: int, y: int) -> PixelClumpResponse:
    store = _store()
    cid = store.clumps.get_clump_id_at_pixel(x, y)
    return PixelClumpResponse(clump_id=cid)


@router.get("/api/pixel/{x}/{y}/spectrum/{datacube_name}", response_model=SpectrumResponse)
def get_pixel_spectrum(x: int, y: int, datacube_name: str) -> SpectrumResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)
    spectrum = extract_pixel_spectrum(dc, x, y)
    figure = create_sed_figure(spectrum, f"Pixel ({x}, {y}) — SED")
    return SpectrumResponse(spectrum=spectrum, figure=figure)


# Region selection.
@router.post("/api/region/spectrum/{datacube_name}", response_model=SpectrumResponse)
def get_region_spectrum(datacube_name: str, body: RegionRequest) -> SpectrumResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)

    mask = np.zeros(dc.spatial_shape, dtype=bool)

    if body.pixels is not None:
        for px in body.pixels:
            x, y = int(px[0]), int(px[1])
            if 0 <= y < dc.ny and 0 <= x < dc.nx:
                mask[y, x] = True
    elif body.rect is not None:
        r = body.rect
        x0, y0 = int(r.x0), int(r.y0)
        x1, y1 = int(r.x1), int(r.y1)
        x0, x1 = max(0, min(x0, x1)), min(dc.nx, max(x0, x1))
        y0, y1 = max(0, min(y0, y1)), min(dc.ny, max(y0, y1))
        mask[y0:y1, x0:x1] = True

    spectrum = extract_region_spectrum(dc, mask)
    figure = create_sed_figure(spectrum, f"Selected Region ({spectrum['n_pixels']} px)")
    return SpectrumResponse(spectrum=spectrum, figure=figure)


# Multi-clump comparison.
@router.post("/api/compare/spectrum/{datacube_name}", response_model=CompareResponse)
def compare_spectra(datacube_name: str, body: CompareRequest) -> CompareResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)

    spectra = []
    labels = []
    for cid in body.clump_ids:
        spec = extract_clump_spectrum(dc, store.clumps, cid)
        spectra.append(spec)
        c = store.clumps.get_clump_by_id(cid)
        labels.append(f"Clump {cid} ({c.component})")

    figure = create_multi_sed_figure(spectra, labels)
    return CompareResponse(figure=figure, spectra=spectra)
