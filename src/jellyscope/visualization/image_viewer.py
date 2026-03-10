"""Plotly figure builders for the galaxy image viewer."""

import numpy as np

from ..data.fits_handler import DataCube
from ..data.clumps import ClumpCatalog


def _asinh_stretch(data: np.ndarray) -> np.ndarray:
    """Apply arcsinh stretch to bring out faint features.

    Standard in astronomy for handling extreme dynamic range.
    """
    finite = data[np.isfinite(data)]
    if len(finite) == 0:
        return data
    vmin = np.percentile(finite, 1)
    vmax = np.percentile(finite, 99.5)
    clipped = np.clip(data, vmin, vmax)
    normalized = (clipped - vmin) / (vmax - vmin + 1e-10)
    return np.arcsinh(normalized * 10) / np.arcsinh(10)


def create_galaxy_heatmap(
    slice_data: np.ndarray,
    filter_name: str,
    colorscale: str = "Viridis",
) -> dict:
    """Create a Plotly heatmap trace for a datacube slice."""
    stretched = _asinh_stretch(slice_data)
    z = []
    for row in stretched:
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
) -> list[dict]:
    """Create Plotly scatter traces for clump boundaries."""
    selected = set(selected_ids or [])
    traces = []
    for cid, boundary in clumps.get_all_boundaries().items():
        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]
        is_selected = cid in selected
        c = clumps.get_clump(cid)
        traces.append({
            "type": "scatter",
            "x": xs,
            "y": ys,
            "mode": "lines",
            "line": {
                "color": "#ff4444" if is_selected else "#00ccff",
                "width": 2.5 if is_selected else 1.2,
            },
            "name": f"Clump {cid}",
            "hoverinfo": "text",
            "text": f"Clump {cid} ({c.component})",
            "showlegend": False,
        })
    return traces


def create_centroid_markers(clumps: ClumpCatalog) -> dict:
    """Create scatter trace of clump centroids with labels."""
    all_clumps = clumps.list_clumps()
    return {
        "type": "scatter",
        "x": [c.x0 for c in all_clumps],
        "y": [c.y0 for c in all_clumps],
        "mode": "markers+text",
        "marker": {"color": "#ffffff", "size": 5, "symbol": "x"},
        "text": [str(c.clump_id) for c in all_clumps],
        "textposition": "top right",
        "textfont": {"color": "#cccccc", "size": 9},
        "hovertemplate": (
            "Clump %{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>"
        ),
        "name": "Centroids",
        "showlegend": False,
    }


def build_viewer_figure(
    datacube: DataCube,
    channel_index: int,
    clumps: ClumpCatalog,
    selected_ids: list[int] | None = None,
    colorscale: str = "Viridis",
) -> dict:
    """Assemble the complete Plotly figure: heatmap + boundaries + centroids."""
    slice_data = datacube.get_slice(channel_index)
    filter_name = datacube.filter_names[channel_index]

    heatmap = create_galaxy_heatmap(slice_data, filter_name, colorscale)
    boundaries = create_clump_boundary_traces(clumps, selected_ids)
    centroids = create_centroid_markers(clumps)

    data = [heatmap] + boundaries + [centroids]

    layout = {
        "title": {
            "text": f"{datacube.name} \u2014 {filter_name}",
            "font": {"color": "#cccccc"},
        },
        "xaxis": {
            "title": "x (pixels)",
            "scaleanchor": "y",
            "constrain": "domain",
            "gridcolor": "#333",
            "color": "#999",
        },
        "yaxis": {
            "title": "y (pixels)",
            "gridcolor": "#333",
            "color": "#999",
        },
        "plot_bgcolor": "#1a1a2e",
        "paper_bgcolor": "#16213e",
        "font": {"color": "#cccccc"},
        "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
        "dragmode": "pan",
    }

    return {"data": data, "layout": layout}
