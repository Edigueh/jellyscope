"""Plotly figure builders for galaxy image viewing."""

from collections.abc import Callable

import numpy as np
from astropy.wcs import WCS

from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog, ClumpProperties
from jellyscope.data.model.coordinates import (
    arcsec_axis,
    image_axis_bounds,
    pixel_scale_arcsec,
    pixels_to_radec_arrays,
)
from jellyscope.model.plotly import (
    ColorBar,
    Figure,
    Font,
    HeatmapTrace,
    Line,
    Marker,
    PlotlyTrace,
    ScatterTrace,
)
from jellyscope.visualization._viz_helpers import (
    GRAY,
    build_dark_axis_layout,
)

# Clump overlay colors. MUST mirror frontend/src/theme.ts (CLUMP_SELECTED_COLOR
# / CLUMP_COLOR / CENTROID_COLOR) — the client recolors these client-side on
# selection, so a mismatch makes clumps flash a different color on select.
_RED: str = "#ff5c5c"  # selected boundary (danger)
_BLUE: str = "#4a9eff"  # unselected boundary (accent)
_WHITE: str = "#e8e8ea"  # centroid marker (ink)


def _estimate_background(data: np.ndarray) -> tuple[float, float]:
    """Estimate background level and noise via sigma-clipped statistics.

    Returns (median, std) from sigma_clipped_stats.
    """
    from astropy.stats import sigma_clipped_stats

    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    _, median, std = sigma_clipped_stats(finite, sigma=3.0, maxiters=5)
    return float(median), float(std)


def _default_alpha(sigma: float) -> float:
    """Default Lupton linear stretch factor from background noise sigma."""
    return 0.02 / (sigma + 1e-10)


def _lupton_asinh_stretch(
    data: np.ndarray, softening: float = 8.0, alpha: float | None = None
) -> np.ndarray:
    """Lupton et al. (2004) asinh stretch: f(x) = arcsinh(alpha*Q*(x-m)) / Q.

    Linear for faint features (x ~ m), logarithmic for bright features.
    Parameters Q and alpha control the transition point.
    """
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return np.zeros_like(data)

    m, sigma = _estimate_background(data)
    if alpha is None:
        alpha = _default_alpha(sigma)

    stretched = np.arcsinh(alpha * softening * (data - m)) / softening

    finite_stretched = stretched[np.isfinite(stretched)]
    if finite_stretched.size == 0:
        return np.zeros_like(data)
    vmax = np.percentile(finite_stretched, 99.5)
    if vmax > 0:
        stretched = stretched / vmax
    stretched = np.clip(stretched, 0.0, 1.0)
    stretched[~np.isfinite(data)] = np.nan
    return stretched


def _log_stretch(data: np.ndarray) -> np.ndarray:
    """Apply log stretch to bring out faint features."""
    from astropy.visualization import AsymmetricPercentileInterval, LogStretch

    finite = data[np.isfinite(data)]
    if len(finite) == 0:
        return data

    # Mask NaN and non-positive values (log is undefined for x <= 0).
    mask = np.logical_or(np.isnan(data), data <= 0.0)
    valid = data[~mask]

    if len(valid) == 0:
        return data

    interval = AsymmetricPercentileInterval(
        lower_percentile=10.0,
        upper_percentile=99.98,
    )
    vmin, vmax = interval.get_limits(valid)

    clipped = np.clip(data, a_min=vmin, a_max=vmax)
    normalized = (clipped - vmin) / (vmax - vmin + 1e-10)

    # Log stretch: f(x) = log(a*x + 1) / log(a + 1)
    # More aggressively boosts faint structure than arcsinh.
    stretch = LogStretch(a=200)
    stretched: np.ndarray = stretch(normalized)

    return stretched


def _normalize_stretch(data: np.ndarray, stretch: str = "log") -> np.ndarray:
    """Apply the named stretch function to bring out faint features."""
    _stretch_map: dict[str, Callable[[np.ndarray], np.ndarray]] = {
        "log": _log_stretch,
        "lupton_asinh": _lupton_asinh_stretch,
    }
    func = _stretch_map.get(stretch, _log_stretch)
    return func(data)


def create_galaxy_heatmap(
    slice_data: np.ndarray,
    colorscale: str = "viridis",
    stretch: str = "log",
    wcs: WCS | None = None,
) -> HeatmapTrace:
    """Create a Plotly heatmap trace for a datacube slice.

    When ``wcs`` is celestial, the trace's ``x``/``y`` arrays are arcsec
    offsets from the image center and per-cell ``customdata`` carries
    ``[x_pix, y_pix, ra_deg, dec_deg]`` so hover reveals pixel + RA/Dec.
    """
    z: list[list[float | None]] = []
    for row in _normalize_stretch(data=slice_data, stretch=stretch):
        z.append([None if np.isnan(v) else float(v) for v in row])

    has_sky = wcs is not None and wcs.has_celestial
    if has_sky:
        ny, nx = slice_data.shape
        sec_pix = pixel_scale_arcsec(wcs)
        return HeatmapTrace(
            z=z,
            colorscale=colorscale,
            hoverongaps=False,
            showscale=True,
            colorbar=ColorBar(title="Flux (stretched)", thickness=15),
            x=arcsec_axis(nx, sec_pix).tolist(),
            y=arcsec_axis(ny, sec_pix).tolist(),
            hovertemplate='sky: (%{x:.3f}", %{y:.3f}")<br>flux: %{z:.4f}<extra></extra>',
        )

    return HeatmapTrace(
        z=z,
        colorscale=colorscale,
        hoverongaps=False,
        showscale=True,
        colorbar=ColorBar(title="Flux (stretched)", thickness=15),
        hovertemplate="x: %{x}<br>y: %{y}<br>flux: %{z:.4f}<extra></extra>",
    )


def _build_clump_boundary_trace(
    cid: int,
    boundary: list[tuple[float, float]],
    c: ClumpProperties,
    *,
    is_selected: bool,
    has_sky: bool,
    sec_pix: float,
    cx: float,
    cy: float,
    wcs: WCS | None,
) -> ScatterTrace:
    """Build a single clump-boundary scatter trace."""
    xs_pix = [p[0] for p in boundary]
    ys_pix = [p[1] for p in boundary]

    if has_sky:
        xs_plot = [(x - cx) * sec_pix for x in xs_pix]
        ys_plot = [(y - cy) * sec_pix for y in ys_pix]
    else:
        xs_plot = list(xs_pix)
        ys_plot = list(ys_pix)

    line = Line(
        color=_RED if is_selected else _BLUE,
        width=2.5 if is_selected else 1.2,
    )

    customdata = _clump_radec_customdata(xs_pix, ys_pix, wcs) if has_sky else None
    if customdata is not None:
        return ScatterTrace(
            x=xs_plot,
            y=ys_plot,
            mode="lines",
            line=line,
            name=f"Clump {cid}",
            showlegend=False,
            customdata=customdata,
            hovertemplate=(
                f"Clump {cid} ({c.component})<br>"
                "pix: (%{customdata[0]:.0f}, %{customdata[1]:.0f})<br>"
                'sky: (%{x:.3f}", %{y:.3f}")<br>'
                "RA: %{customdata[2]:.6f}°<br>"
                "Dec: %{customdata[3]:.6f}°<extra></extra>"
            ),
        )

    return ScatterTrace(
        x=xs_plot,
        y=ys_plot,
        mode="lines",
        line=line,
        name=f"Clump {cid}",
        showlegend=False,
        hoverinfo="text",
        text=f"Clump {cid} ({c.component})",
    )


def _clump_radec_customdata(
    xs_pix: list[float], ys_pix: list[float], wcs: WCS | None
) -> list[list[float | None]] | None:
    """Per-vertex ``[x_pix, y_pix, ra|None, dec|None]``; ``None`` if conversion fails."""
    if wcs is None:
        return None
    try:
        ra_arr, dec_arr, finite = pixels_to_radec_arrays(xs_pix, ys_pix, wcs)
    except Exception:  # pragma: no cover - defensive
        return None
    return [
        [
            float(xp),
            float(yp),
            float(ra) if ok else None,
            float(dec) if ok else None,
        ]
        for xp, yp, ra, dec, ok in zip(xs_pix, ys_pix, ra_arr, dec_arr, finite, strict=True)
    ]


def create_clump_boundary_traces(
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    wcs: WCS | None = None,
) -> list[ScatterTrace]:
    """Create Plotly scatter traces for clump boundaries.

    When ``wcs`` is celestial, vertices are placed in arcsec offsets from the
    image center and each carries ``[x_pix, y_pix, ra_deg, dec_deg]`` in
    ``customdata`` for hover.
    """
    select = set(selected_ids or [])
    has_sky = wcs is not None and wcs.has_celestial
    sec_pix = pixel_scale_arcsec(wcs) if has_sky else 0.0
    cx = (clumps.nx - 1) / 2.0
    cy = (clumps.ny - 1) / 2.0

    traces: list[ScatterTrace] = []
    for cid, boundary in clumps.get_all_boundaries().items():
        traces.append(
            _build_clump_boundary_trace(
                cid,
                boundary,
                clumps.get_clump_by_id(cid),
                is_selected=cid in select,
                has_sky=has_sky,
                sec_pix=sec_pix,
                cx=cx,
                cy=cy,
                wcs=wcs,
            )
        )
    return traces


def create_centroid_markers(
    clumps: ClumpCatalog,
    *,
    has_sky: bool,
    sec_pix: float,
) -> ScatterTrace:
    """Create scatter trace of clump centroids with labels."""
    all_clumps: list[ClumpProperties] = clumps.list_clumps()
    cx = (clumps.nx - 1) / 2.0
    cy = (clumps.ny - 1) / 2.0

    if has_sky and sec_pix > 0:
        xs_plot = [(c.x0 - cx) * sec_pix for c in all_clumps]
        ys_plot = [(c.y0 - cy) * sec_pix for c in all_clumps]
    else:
        xs_plot = [c.x0 for c in all_clumps]
        ys_plot = [c.y0 for c in all_clumps]

    if has_sky:
        return ScatterTrace(
            x=xs_plot,
            y=ys_plot,
            mode="markers+text",
            marker=Marker(color=_WHITE, size=5, symbol="x"),
            text=[str(c.clump_id) for c in all_clumps],
            textposition="top right",
            textfont=Font(color=GRAY, size=9),
            name="Centroids",
            showlegend=False,
            customdata=[[c.x0, c.y0, c.ra_deg, c.dec_deg] for c in all_clumps],
            hovertemplate=(
                "Clump %{text}<br>"
                "pix: (%{customdata[0]:.1f}, %{customdata[1]:.1f})<br>"
                'sky: (%{x:.3f}", %{y:.3f}")<br>'
                "RA: %{customdata[2]:.6f}°<br>"
                "Dec: %{customdata[3]:.6f}°<extra></extra>"
            ),
        )

    return ScatterTrace(
        x=xs_plot,
        y=ys_plot,
        mode="markers+text",
        marker=Marker(color=_WHITE, size=5, symbol="x"),
        text=[str(c.clump_id) for c in all_clumps],
        textposition="top right",
        textfont=Font(color=GRAY, size=9),
        name="Centroids",
        showlegend=False,
        hovertemplate="Clump %{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>",
    )


def build_viewer_figure(
    datacube: DataCube,
    channel_index: int,
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    colorscale: str = "Viridis",
    stretch: str = "log",
) -> Figure:
    """Assembles heatmap + boundaries + centroids."""
    slice_data: np.ndarray = datacube.get_slice_by_channel_index(channel_index)

    has_sky = datacube.wcs is not None and datacube.wcs.has_celestial
    axis_label_x = "x offset (arcsec)" if has_sky else "x (pixels)"
    axis_label_y = "y offset (arcsec)" if has_sky else "y (pixels)"

    ny, nx = slice_data.shape
    sec_pix = pixel_scale_arcsec(datacube.wcs) if has_sky else None
    bounds = image_axis_bounds(nx, ny, sec_pix)

    heatmap = create_galaxy_heatmap(slice_data, colorscale, stretch, wcs=datacube.wcs)
    boundaries = create_clump_boundary_traces(clumps, selected_ids, wcs=datacube.wcs)
    centroids = create_centroid_markers(clumps, has_sky=has_sky, sec_pix=sec_pix or 0.0)

    data: list[PlotlyTrace] = [heatmap, *boundaries, centroids]

    layout = build_dark_axis_layout(
        title_text="",
        axis_label_x=axis_label_x,
        axis_label_y=axis_label_y,
        bounds=bounds,
        wcs=datacube.wcs,
        nx=nx,
        ny=ny,
    )

    return Figure(data=data, layout=layout)
