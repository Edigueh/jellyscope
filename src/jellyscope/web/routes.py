"""REST API endpoints and page routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from starlette.responses import HTMLResponse, Response

from jellyscope.data.data_store import DataStore
from jellyscope.model.schemas import (
    ClumpDetailResponse,
    ClumpListItem,
    ClumpsListResponse,
    DatacubesResponse,
    FilterInfo,
    FiltersResponse,
    PixelClumpResponse,
    ViewerResponse,
)
from jellyscope.visualization.image_viewer import build_viewer_figure
from jellyscope.visualization.properties_panel import format_clump_properties

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
    from jellyscope.config import NIRCAM_WAVELENGTHS

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
@router.get("/api/viewer/{datacube_name}/{channel_index}", response_model=ViewerResponse)
def get_viewer_figure(
    datacube_name: str,
    channel_index: int,
    selected: Annotated[str, Query()] = "",
    colorscale: Annotated[str, Query()] = "Viridis",
) -> ViewerResponse:
    store = _store()
    dc = store.get_datacube(datacube_name)
    selected_ids: list[int] = (
        [int(i) for i in selected.split(",") if i.strip()] if selected else []
    )
    figure: dict[str, Any] = build_viewer_figure(
        dc, channel_index, store.clumps, selected_ids, colorscale
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


# Pixel Interaction.
@router.get("/api/pixel/{x}/{y}/clump", response_model=PixelClumpResponse)
def get_pixel_clump(x: int, y: int) -> PixelClumpResponse:
    store = _store()
    cid = store.clumps.get_clump_id_at_pixel(x, y)
    return PixelClumpResponse(clump_id=cid)
