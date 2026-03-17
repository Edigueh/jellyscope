"""REST API endpoints and page routes."""

import numpy as np
from flask import Blueprint, Response, jsonify, render_template, request

from ..analysis.spectral import (
    extract_clump_spectrum,
    extract_pixel_spectrum,
    extract_region_spectrum,
)
from ..data.cache import DataStore
from ..visualization.image_viewer import build_viewer_figure
from ..visualization.properties_panel import format_clump_properties
from ..visualization.spectrum_plot import create_multi_sed_figure, create_sed_figure

bp = Blueprint("api", __name__)


def _store() -> DataStore:
    return DataStore.get()


# --- Pages ---


@bp.route("/")
def index() -> str:
    store = _store()
    return render_template(
        "index.html",
        datacubes=store.list_datacubes(),
        filters=store.get_datacube("nircam").filter_names,
    )


# --- Datacube info ---


@bp.route("/api/datacubes")
def list_datacubes() -> Response:
    store = _store()
    return jsonify({"datacubes": store.list_datacubes()})


@bp.route("/api/filters/<datacube_name>")
def list_filters(datacube_name: str) -> Response:
    dc = _store().get_datacube(datacube_name)
    from ..config import NIRCAM_WAVELENGTHS

    filters = []
    for i, name in enumerate(dc.filter_names):
        filters.append(
            {
                "index": i,
                "name": name,
                "wavelength": NIRCAM_WAVELENGTHS.get(name, 0.0),
            }
        )
    return jsonify({"filters": filters})


# --- Image viewer ---


@bp.route("/api/viewer/<datacube_name>/<int:channel_index>")
def get_viewer_figure(datacube_name: str, channel_index: int) -> Response:
    store = _store()
    dc = store.get_datacube(datacube_name)
    selected_str = request.args.get("selected", "")
    selected_ids = [int(x) for x in selected_str.split(",") if x.strip()] if selected_str else []
    colorscale = request.args.get("colorscale", "Viridis")
    figure = build_viewer_figure(dc, channel_index, store.clumps, selected_ids, colorscale)
    return jsonify({"figure": figure, "filter_name": dc.filter_names[channel_index]})


# --- Clumps ---


@bp.route("/api/clumps")
def list_clumps() -> Response:
    store = _store()
    component = request.args.get("component")
    inside_param = request.args.get("inside")
    is_inside: bool | None = None
    if inside_param is not None:
        is_inside = inside_param.lower() == "true"
    clumps = store.clumps.filter_clumps(component=component, inside=is_inside)
    return jsonify(
        {
            "clumps": [
                {
                    "clump_id": c.clump_id,
                    "x0": round(c.x0, 2),
                    "y0": round(c.y0, 2),
                    "area_pix": c.area_pix,
                    "component": c.component,
                    "inside": c.inside,
                }
                for c in clumps
            ]
        }
    )


@bp.route("/api/clumps/<int:clump_id>")
def get_clump(clump_id: int) -> Response:
    store = _store()
    clump = store.clumps.get_clump(clump_id)
    boundary = store.clumps.get_boundary_coords(clump_id)
    props = format_clump_properties(clump)
    return jsonify({"properties": props, "boundary": boundary})


@bp.route("/api/clumps/<int:clump_id>/spectrum/<datacube_name>")
def get_clump_spectrum(clump_id: int, datacube_name: str) -> Response:
    store = _store()
    dc = store.get_datacube(datacube_name)
    spectrum = extract_clump_spectrum(dc, store.clumps, clump_id)
    figure = create_sed_figure(spectrum, f"Clump {clump_id} — SED")
    return jsonify({"spectrum": spectrum, "figure": figure})


# --- Pixel interaction ---


@bp.route("/api/pixel/<int:x>/<int:y>/clump")
def get_pixel_clump(x: int, y: int) -> Response:
    store = _store()
    cid = store.clumps.get_clump_at_pixel(x, y)
    return jsonify({"clump_id": cid})


@bp.route("/api/pixel/<int:x>/<int:y>/spectrum/<datacube_name>")
def get_pixel_spectrum(x: int, y: int, datacube_name: str) -> Response:
    store = _store()
    dc = store.get_datacube(datacube_name)
    spectrum = extract_pixel_spectrum(dc, x, y)
    figure = create_sed_figure(spectrum, f"Pixel ({x}, {y}) — SED")
    return jsonify({"spectrum": spectrum, "figure": figure})


# --- Region selection ---


@bp.route("/api/region/spectrum/<datacube_name>", methods=["POST"])
def get_region_spectrum(datacube_name: str) -> Response:
    store = _store()
    dc = store.get_datacube(datacube_name)
    body = request.get_json()

    mask = np.zeros(dc.spatial_shape, dtype=bool)

    if "pixels" in body:
        for px in body["pixels"]:
            x, y = int(px[0]), int(px[1])
            if 0 <= y < dc.ny and 0 <= x < dc.nx:
                mask[y, x] = True
    elif "rect" in body:
        r = body["rect"]
        x0, y0 = int(r["x0"]), int(r["y0"])
        x1, y1 = int(r["x1"]), int(r["y1"])
        x0, x1 = max(0, min(x0, x1)), min(dc.nx, max(x0, x1))
        y0, y1 = max(0, min(y0, y1)), min(dc.ny, max(y0, y1))
        mask[y0:y1, x0:x1] = True

    spectrum = extract_region_spectrum(dc, mask)
    figure = create_sed_figure(spectrum, f"Selected Region ({spectrum['n_pixels']} px)")
    return jsonify({"spectrum": spectrum, "figure": figure})


# --- Multi-clump comparison ---


@bp.route("/api/compare/spectrum/<datacube_name>", methods=["POST"])
def compare_spectra(datacube_name: str) -> Response:
    store = _store()
    dc = store.get_datacube(datacube_name)
    body = request.get_json()
    clump_ids = body.get("clump_ids", [])

    spectra = []
    labels = []
    for cid in clump_ids:
        spec = extract_clump_spectrum(dc, store.clumps, cid)
        spectra.append(spec)
        c = store.clumps.get_clump(cid)
        labels.append(f"Clump {cid} ({c.component})")

    figure = create_multi_sed_figure(spectra, labels)
    return jsonify({"figure": figure, "spectra": spectra})
