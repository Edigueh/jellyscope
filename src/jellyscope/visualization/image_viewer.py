"""Plotly figure builders for galaxy image viewing."""

from collections.abc import Callable
from typing import Any

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
from jellyscope.visualization._viz_helpers import (
    GRAY,
    RADEC_HOVER_PREFIX,
    build_dark_axis_layout,
    build_radec_customdata_grid,
)

_RED: str = "#ff4444"
_BLUE: str = "#00ccff"
_WHITE: str = "#ffffff"


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
        alpha = 0.02 / (sigma + 1e-10)

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


def _power_stretch(data: np.ndarray) -> np.ndarray:  # pragma: no cover
    """Power stretch — tunable, lower exponent = more aggressive on faint features."""
    from astropy.visualization import PowerStretch

    finite = data[np.isfinite(data)]
    if len(finite) == 0:
        return data

    vmin = np.percentile(finite, 20)
    vmax = np.percentile(finite, 99.5)
    clipped = np.clip(data, a_min=vmin, a_max=vmax)
    normalized = (clipped - vmin) / (vmax - vmin + 1e-10)

    stretch = PowerStretch(a=0.5)
    stretched: np.ndarray = stretch(normalized)
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
        "power": _power_stretch,
    }
    func = _stretch_map.get(stretch, _log_stretch)
    return func(data)


def create_galaxy_heatmap(
    slice_data: np.ndarray,
    colorscale: str = "viridis",
    stretch: str = "log",
    wcs: WCS | None = None,
) -> dict[str, Any]:
    """Create a Plotly heatmap trace for a datacube slice.

    When ``wcs`` is celestial, the trace's ``x``/``y`` arrays are arcsec
    offsets from the image center and per-cell ``customdata`` carries
    ``[x_pix, y_pix, ra_deg, dec_deg]`` so hover reveals pixel + RA/Dec.
    """
    z = []
    for row in _normalize_stretch(data=slice_data, stretch=stretch):
        z.append([None if np.isnan(v) else float(v) for v in row])

    trace: dict[str, Any] = {
        "type": "heatmap",
        "z": z,
        "colorscale": colorscale,
        "hoverongaps": False,
        "showscale": True,
        "colorbar": {"title": "Flux (stretched)", "thickness": 15},
    }

    has_sky = wcs is not None and wcs.has_celestial
    if has_sky:
        ny, nx = slice_data.shape
        sec_pix = pixel_scale_arcsec(wcs)
        trace["x"] = arcsec_axis(nx, sec_pix).tolist()
        trace["y"] = arcsec_axis(ny, sec_pix).tolist()
        trace["customdata"] = build_radec_customdata_grid(nx, ny, wcs)
        trace["hovertemplate"] = RADEC_HOVER_PREFIX + "flux: %{z:.4f}<extra></extra>"
    else:
        trace["hovertemplate"] = "x: %{x}<br>y: %{y}<br>flux: %{z:.4f}<extra></extra>"

    return trace


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
) -> dict[str, Any]:
    """Build a single clump-boundary scatter trace."""
    xs_pix = [p[0] for p in boundary]
    ys_pix = [p[1] for p in boundary]

    if has_sky:
        xs_plot = [(x - cx) * sec_pix for x in xs_pix]
        ys_plot = [(y - cy) * sec_pix for y in ys_pix]
    else:
        xs_plot = list(xs_pix)
        ys_plot = list(ys_pix)

    trace: dict[str, Any] = {
        "type": "scatter",
        "x": xs_plot,
        "y": ys_plot,
        "mode": "lines",
        "line": {
            "color": _RED if is_selected else _BLUE,
            "width": 2.5 if is_selected else 1.2,
        },
        "name": f"Clump {cid}",
        "showlegend": False,
    }

    customdata = _clump_radec_customdata(xs_pix, ys_pix, wcs) if has_sky else None
    if customdata is not None:
        trace["customdata"] = customdata
        trace["hovertemplate"] = (
            f"Clump {cid} ({c.component})<br>"
            "pix: (%{customdata[0]:.0f}, %{customdata[1]:.0f})<br>"
            'sky: (%{x:.3f}", %{y:.3f}")<br>'
            "RA: %{customdata[2]:.6f}°<br>"
            "Dec: %{customdata[3]:.6f}°<extra></extra>"
        )
    else:
        trace["hoverinfo"] = "text"
        trace["text"] = f"Clump {cid} ({c.component})"
    return trace


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
) -> list[dict[str, Any]]:
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

    traces: list[dict[str, Any]] = []
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


def create_centroid_markers(clumps: ClumpCatalog, wcs: WCS | None = None) -> dict[str, Any]:
    """Create scatter trace of clump centroids with labels."""
    all_clumps: list[ClumpProperties] = clumps.list_clumps()
    has_sky = (wcs is not None and wcs.has_celestial) or any(
        c.ra_deg is not None for c in all_clumps
    )
    sec_pix = pixel_scale_arcsec(wcs) if (wcs is not None and wcs.has_celestial) else 0.0
    cx = (clumps.nx - 1) / 2.0
    cy = (clumps.ny - 1) / 2.0

    if has_sky and sec_pix > 0:
        xs_plot = [(c.x0 - cx) * sec_pix for c in all_clumps]
        ys_plot = [(c.y0 - cy) * sec_pix for c in all_clumps]
    else:
        xs_plot = [c.x0 for c in all_clumps]
        ys_plot = [c.y0 for c in all_clumps]

    trace: dict[str, Any] = {
        "type": "scatter",
        "x": xs_plot,
        "y": ys_plot,
        "mode": "markers+text",
        "marker": {"color": _WHITE, "size": 5, "symbol": "x"},
        "text": [str(c.clump_id) for c in all_clumps],
        "textposition": "top right",
        "textfont": {"color": GRAY, "size": 9},
        "name": "Centroids",
        "showlegend": False,
    }

    if has_sky:
        trace["customdata"] = [[c.x0, c.y0, c.ra_deg, c.dec_deg] for c in all_clumps]
        trace["hovertemplate"] = (
            "Clump %{text}<br>"
            "pix: (%{customdata[0]:.1f}, %{customdata[1]:.1f})<br>"
            'sky: (%{x:.3f}", %{y:.3f}")<br>'
            "RA: %{customdata[2]:.6f}°<br>"
            "Dec: %{customdata[3]:.6f}°<extra></extra>"
        )
    else:
        trace["hovertemplate"] = "Clump %{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>"
    return trace


def build_viewer_figure(
    datacube: DataCube,
    channel_index: int,
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    colorscale: str = "Viridis",
    stretch: str = "log",
) -> dict[str, Any]:
    """Assembles heatmap + boundaries + centroids."""
    slice_data: np.ndarray = datacube.get_slice_by_channel_index(channel_index)
    filter_name: str = datacube.filter_names[channel_index]

    has_sky = datacube.wcs is not None and datacube.wcs.has_celestial
    axis_label_x = "x offset (arcsec)" if has_sky else "x (pixels)"
    axis_label_y = "y offset (arcsec)" if has_sky else "y (pixels)"

    ny, nx = slice_data.shape
    sec_pix = pixel_scale_arcsec(datacube.wcs) if has_sky else None
    bounds = image_axis_bounds(nx, ny, sec_pix)

    heatmap: dict[str, Any] = create_galaxy_heatmap(
        slice_data, colorscale, stretch, wcs=datacube.wcs
    )
    boundaries: list[dict[str, Any]] = create_clump_boundary_traces(
        clumps, selected_ids, wcs=datacube.wcs
    )
    centroids: dict[str, Any] = create_centroid_markers(clumps, wcs=datacube.wcs)

    # *boundaries unpacks the list from. E.g: boundaries = [a, b, c...]; *boundaries = a, b, c...
    data: list[dict[str, Any]] = [heatmap, *boundaries, centroids]

    layout: dict[str, Any] = build_dark_axis_layout(
        title_text=f"{datacube.name} \u2014 {filter_name}",
        axis_label_x=axis_label_x,
        axis_label_y=axis_label_y,
        bounds=bounds,
    )

    return {"data": data, "layout": layout}
