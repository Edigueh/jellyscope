"""Plotly figure builders for galaxy image viewing."""

from collections.abc import Callable
from typing import Any

import numpy as np

from jellyscope.data.data_store import DataCube
from jellyscope.data.model.clumps import ClumpCatalog, ClumpProperties

_RED: str = "#ff4444"
_BLUE: str = "#00ccff"
_WHITE: str = "#ffffff"
_GRAY: str = "#cccccc"
_DARK_GRAY: str = "#999"
_SOFT_BLACK: str = "#333"
_DARK_BLUE: str = "#1a1a2e"
_SOFT_DARK_BLUE: str = "#16213e"


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
) -> dict[str, Any]:
    """Create a Plotly heatmap trace for a datacube slice."""
    z = []
    for row in _normalize_stretch(data=slice_data, stretch=stretch):
        z.append([None if np.isnan(v) else float(v) for v in row])
    return {
        "type": "heatmap",
        "z": z,
        "colorscale": colorscale,
        "hoverongaps": False,
        "hovertemplate": "x: %{x}<br>y: %{y}<br>flux: %{z:.4f}<extra></extra>",
        "showscale": True,
        "colorbar": {"title": "Flux (stretched)", "thickness": 15},
    }


def create_clump_boundary_traces(
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Create Plotly scatter traces for clump boundaries."""
    select = set(selected_ids or [])
    traces: list[dict[str, Any]] = []
    for cid, boundary in clumps.get_all_boundaries().items():
        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]
        is_selected = cid in select
        c: ClumpProperties = clumps.get_clump_by_id(cid)
        traces.append(
            {
                "type": "scatter",
                "x": xs,
                "y": ys,
                "mode": "lines",
                "line": {
                    "color": _RED if is_selected else _BLUE,
                    "width": 2.5 if is_selected else 1.2,
                },
                "name": f"Clump {cid}",
                "hoverinfo": "text",
                "text": f"Clump {cid} ({c.component})",
                "showlegend": False,
            }
        )
    return traces


def create_centroid_markers(clumps: ClumpCatalog) -> dict[str, Any]:
    """Create scatter trace of clump centroids with labels."""
    all_clumps: list[ClumpProperties] = clumps.list_clumps()
    return {
        "type": "scatter",
        "x": [c.x0 for c in all_clumps],
        "y": [c.y0 for c in all_clumps],
        "mode": "markers+text",
        "marker": {"color": _WHITE, "size": 5, "symbol": "x"},
        "text": [str(c.clump_id) for c in all_clumps],
        "textposition": "top right",
        "textfont": {"color": _GRAY, "size": 9},
        "hovertemplate": ("Clump %{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>"),
        "name": "Centroids",
        "showlegend": False,
    }


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

    heatmap: dict[str, Any] = create_galaxy_heatmap(slice_data, colorscale, stretch)
    boundaries: list[dict[str, Any]] = create_clump_boundary_traces(clumps, selected_ids)
    centroids: dict[str, Any] = create_centroid_markers(clumps)

    # *boundaries unpacks the list from. E.g: boundaries = [a, b, c...]; *boundaries = a, b, c...
    data: list[dict[str, Any]] = [heatmap, *boundaries, centroids]

    layout: dict[str, Any] = {
        "title": {
            "text": f"{datacube.name} \u2014 {filter_name}",
            "font": {"color": _GRAY},
        },
        "xaxis": {
            "title": "x (pixels)",
            "scaleanchor": "y",
            "constrain": "domain",
            "gridcolor": _SOFT_BLACK,
            "color": _DARK_GRAY,
        },
        "yaxis": {
            "title": "y (pixels)",
            "gridcolor": _SOFT_BLACK,
            "color": _DARK_GRAY,
        },
        "plot_bgcolor": _DARK_BLUE,
        "paper_bgcolor": _SOFT_DARK_BLUE,
        "font": {"color": _GRAY},
        "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
        "dragmode": "pan",
    }

    return {"data": data, "layout": layout}
