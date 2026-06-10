"""REST API endpoints and page routes."""

from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import HTMLResponse, Response

from jellyscope.config import NIRCAM_WAVELENGTHS
from jellyscope.data.data_store import Dataset, DataStore
from jellyscope.data.model.coordinates import skycoord_separation_arcsec
from jellyscope.model.schemas import (
    ClumpDetailResponse,
    ClumpListItem,
    ClumpSeparation,
    ClumpSeparationsResponse,
    ClumpsListResponse,
    DatacubesResponse,
    DatasetsResponse,
    FilterInfo,
    FiltersResponse,
    PixelClumpResponse,
    RGBViewerResponse,
    ViewerResponse,
)
from jellyscope.visualization.image_viewer import build_viewer_figure
from jellyscope.visualization.properties_panel import format_clump_properties
from jellyscope.visualization.rgb_composite import build_rgb_figure

router = APIRouter()


def _store() -> DataStore:
    return DataStore.get()


def _dataset(name: str) -> Dataset:
    try:
        return _store().get_dataset(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# Pages.
@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> Response:
    store = _store()
    default_dataset = store.default_dataset
    default_ds = store.get_dataset(default_dataset)
    # Pick first available datacube of the default dataset for the initial UI.
    default_datacube = default_ds.list_datacubes()[0]
    return request.app.state.templates.TemplateResponse(  # type: ignore[no-any-return]
        request,
        "index.html",
        {
            "datasets": store.list_datasets(),
            "default_dataset": default_dataset,
            "default_datacube": default_datacube,
            "datacubes": default_ds.list_datacubes(),
            "filters": default_ds.get_datacube(default_datacube).filter_names,
            "wavelengths": NIRCAM_WAVELENGTHS,
        },
    )


# Datasets.
@router.get("/api/datasets", response_model=DatasetsResponse)
def list_datasets() -> DatasetsResponse:
    store = _store()
    return DatasetsResponse(datasets=store.list_datasets(), default=store.default_dataset)


# Datacube info.
@router.get("/api/datasets/{dataset_name}/datacubes", response_model=DatacubesResponse)
def list_datacubes(dataset_name: str) -> DatacubesResponse:
    ds = _dataset(dataset_name)
    return DatacubesResponse(datacubes=ds.list_datacubes())


@router.get("/api/datasets/{dataset_name}/filters/{datacube_name}", response_model=FiltersResponse)
def list_filters(dataset_name: str, datacube_name: str) -> FiltersResponse:
    dc = _dataset(dataset_name).get_datacube(datacube_name)

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
@router.get(
    "/api/datasets/{dataset_name}/viewer/{datacube_name}/rgb", response_model=RGBViewerResponse
)
def get_rgb_viewer_figure(
    dataset_name: str,
    datacube_name: str,
    r: Annotated[int, Query(description="Red channel filter index")],
    g: Annotated[int, Query(description="Green channel filter index")],
    b: Annotated[int, Query(description="Blue channel filter index")],
    selected: Annotated[str, Query()] = "",
    method: Annotated[Literal["percentile_asinh", "lupton"], Query()] = "percentile_asinh",
    softening: Annotated[float, Query()] = 8.0,
) -> RGBViewerResponse:
    ds = _dataset(dataset_name)
    dc = ds.get_datacube(datacube_name)
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
    assert ds.clumps is not None
    figure: dict[str, Any] = build_rgb_figure(
        dc, r, g, b, ds.clumps, selected_ids, method=method, softening=softening
    )
    return RGBViewerResponse(
        figure=figure,
        r_filter=dc.filter_names[r],
        g_filter=dc.filter_names[g],
        b_filter=dc.filter_names[b],
    )


@router.get(
    "/api/datasets/{dataset_name}/viewer/{datacube_name}/{channel_index}",
    response_model=ViewerResponse,
)
def get_viewer_figure(
    dataset_name: str,
    datacube_name: str,
    channel_index: int,
    selected: Annotated[str, Query()] = "",
    colorscale: Annotated[str, Query()] = "Viridis",
    stretch: Annotated[Literal["log", "lupton_asinh", "power"], Query()] = "log",
) -> ViewerResponse:
    ds = _dataset(dataset_name)
    dc = ds.get_datacube(datacube_name)
    if not 0 <= channel_index < dc.n_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Channel index {channel_index} out of range [0, {dc.n_channels})",
        )
    selected_ids: list[int] = (
        [int(i) for i in selected.split(",") if i.strip()] if selected else []
    )
    assert ds.clumps is not None
    figure: dict[str, Any] = build_viewer_figure(
        dc, channel_index, ds.clumps, selected_ids, colorscale, stretch
    )
    return ViewerResponse(figure=figure, filter_name=dc.filter_names[channel_index])


# Clumps.
@router.get("/api/datasets/{dataset_name}/clumps", response_model=ClumpsListResponse)
def list_clumps(
    dataset_name: str,
    component: Annotated[str | None, Query()] = None,
    inside: Annotated[bool | None, Query()] = None,
) -> ClumpsListResponse:
    ds = _dataset(dataset_name)
    assert ds.clumps is not None
    clumps = ds.clumps.filter_clumps(component, inside)
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


@router.get(
    "/api/datasets/{dataset_name}/clumps/separations",
    response_model=ClumpSeparationsResponse,
)
def get_clump_separations(dataset_name: str) -> ClumpSeparationsResponse:
    """Pairwise angular separations between all clump centroids.

    Uses cached SkyCoord centroids from ``ClumpCatalog.attach_skycoords``.
    Returns 422 when the dataset's WCS lacks celestial axes. ``sep_pc`` is
    always ``None`` until a galaxy distance is configured (option A).
    """
    ds = _dataset(dataset_name)
    assert ds.clumps is not None
    coords = ds.clumps.centroid_skycoords()
    if coords is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Dataset '{dataset_name}' has no celestial WCS — RA/Dec "
                "unavailable, cannot compute separations."
            ),
        )

    clump_list = ds.clumps.list_clumps()
    pairs: list[ClumpSeparation] = []
    n = len(clump_list)
    for i in range(n):
        ra_i = clump_list[i].ra_deg
        dec_i = clump_list[i].dec_deg
        if ra_i is None or dec_i is None:
            continue
        for j in range(i + 1, n):
            ra_j = clump_list[j].ra_deg
            dec_j = clump_list[j].dec_deg
            if ra_j is None or dec_j is None:
                continue
            sep = skycoord_separation_arcsec(coords[i], coords[j])
            if not np.isfinite(sep):
                continue
            pairs.append(
                ClumpSeparation(
                    clump_a=clump_list[i].clump_id,
                    clump_b=clump_list[j].clump_id,
                    sep_arcsec=float(sep),
                    sep_pc=None,
                )
            )

    return ClumpSeparationsResponse(distance_mpc=None, pairs=pairs)


@router.get("/api/datasets/{dataset_name}/clumps/{clump_id}", response_model=ClumpDetailResponse)
def get_clump(dataset_name: str, clump_id: int) -> ClumpDetailResponse:
    ds = _dataset(dataset_name)
    assert ds.clumps is not None
    clump = ds.clumps.get_clump_by_id(clump_id)
    boundary = ds.clumps.get_boundary_coords(clump_id)
    props = format_clump_properties(clump)
    return ClumpDetailResponse(
        properties=props,
        boundary=[list(coord) for coord in boundary],
    )


# Pixel Interaction.
@router.get("/api/datasets/{dataset_name}/pixel/{x}/{y}/clump", response_model=PixelClumpResponse)
def get_pixel_clump(dataset_name: str, x: int, y: int) -> PixelClumpResponse:
    ds = _dataset(dataset_name)
    assert ds.clumps is not None
    cid = ds.clumps.get_clump_id_at_pixel(x, y)
    return PixelClumpResponse(clump_id=cid)
