"""Static prebake: dump all API payloads to disk for GitHub Pages hosting.

Walks the ``DataStore``, calls the existing visualization builders once per
(dataset, cube, channel, stretch) and per (dataset, cube, RGB preset), and
writes the resulting Plotly figure dicts as gzipped JSON. Emits everything
under ``--out`` in a layout the static frontend expects — see
``docs/data/manifest.json``.

Byte-for-byte compatibility with the live FastAPI responses is a design
goal; ``tests/scripts/test_prebake_parity.py`` guards against drift.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from jellyscope.config import NIRCAM_WAVELENGTHS, JellyscopeConfig
from jellyscope.data.data_store import DataStore
from jellyscope.data.model.clumps import ClumpCatalog
from jellyscope.data.model.coordinates import skycoord_separation_arcsec
from jellyscope.data.model.datacube import DataCube
from jellyscope.model.schemas import (
    ClumpDetailResponse,
    ClumpListItem,
    ClumpSeparation,
    ClumpSeparationsResponse,
    ClumpsListResponse,
    FilterInfo,
    RGBViewerResponse,
    ViewerResponse,
)
from jellyscope.visualization.image_viewer import build_viewer_figure
from jellyscope.visualization.properties_panel import format_clump_properties
from jellyscope.visualization.rgb_composite import build_rgb_figure

logger = logging.getLogger("prebake")

# Preset RGB triples baked for every datacube that has all three filters.
# Falls back to (last, mid, first) index triple when a preset's filters aren't
# available, so every dataset ships at least one RGB even with reduced filter
# sets.
RGB_PRESETS: list[tuple[str, str, str]] = [
    ("F444W", "F200W", "F070W"),
    ("F444W", "F150W", "F090W"),
    ("F410M", "F200W", "F115W"),
]

STRETCHES: list[str] = ["log", "lupton_asinh"]


@dataclass(frozen=True)
class BakeStats:
    datasets: int = 0
    viewer_figures: int = 0
    rgb_figures: int = 0
    clump_details: int = 0
    bytes_written: int = 0


def _write_json(path: Path, payload: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    return len(raw)


def _preset_indices(dc: DataCube, preset: tuple[str, str, str]) -> tuple[int, int, int] | None:
    try:
        return (
            dc.filter_names.index(preset[0]),
            dc.filter_names.index(preset[1]),
            dc.filter_names.index(preset[2]),
        )
    except ValueError:
        return None


def _bake_viewer(
    out: Path,
    dataset: str,
    cube_name: str,
    dc: DataCube,
    clumps: ClumpCatalog,
) -> tuple[int, int]:
    """Bake every (channel, stretch) as JSON. Returns (count, bytes)."""
    count = 0
    total = 0
    for ch in range(dc.n_channels):
        for stretch in STRETCHES:
            figure = build_viewer_figure(dc, ch, clumps, [], "Viridis", stretch)
            payload = ViewerResponse(figure=figure, filter_name=dc.filter_names[ch]).model_dump(
                mode="json", exclude_none=True
            )
            path = out / dataset / "viewer" / cube_name / stretch / f"{ch}.json"
            total += _write_json(path, payload)
            count += 1
    return count, total


def _bake_rgb(
    out: Path,
    dataset: str,
    cube_name: str,
    dc: DataCube,
    clumps: ClumpCatalog,
) -> tuple[list[dict[str, Any]], int, int]:
    """Bake every RGB preset that resolves. Returns (manifest_entries, count, bytes)."""
    entries: list[dict[str, Any]] = []
    count = 0
    total = 0
    for preset in RGB_PRESETS:
        idx = _preset_indices(dc, preset)
        if idx is None:
            continue
        r, g, b = idx
        figure = build_rgb_figure(
            dc, r, g, b, clumps, [], method="percentile_asinh", softening=8.0
        )
        payload = RGBViewerResponse(
            figure=figure,
            r_filter=dc.filter_names[r],
            g_filter=dc.filter_names[g],
            b_filter=dc.filter_names[b],
        ).model_dump(mode="json", exclude_none=True)
        key = f"{r}-{g}-{b}"
        path = out / dataset / "rgb" / cube_name / f"{key}.json"
        total += _write_json(path, payload)
        count += 1
        entries.append({"r": r, "g": g, "b": b, "labels": list(preset), "key": key})
    return entries, count, total


def _bake_clumps(
    out: Path,
    dataset: str,
    clumps: ClumpCatalog,
) -> tuple[int, int]:
    """Emit clumps.json (list) + per-id detail + separations + pixel index."""
    total = 0

    items = [
        ClumpListItem(
            clump_id=c.clump_id,
            x0=round(c.x0, 2),
            y0=round(c.y0, 2),
            area_pix=c.area_pix,
            component=c.component,
            inside=c.inside,
        )
        for c in clumps.list_clumps()
    ]
    total += _write_json(
        out / dataset / "clumps.json",
        ClumpsListResponse(clumps=items).model_dump(mode="json"),
    )

    detail_dir = out / dataset / "clump"
    detail_count = 0
    for c in clumps.list_clumps():
        detail = ClumpDetailResponse(
            properties=format_clump_properties(c),
            boundary=clumps.get_boundary_coords(c.clump_id),
        ).model_dump(mode="json")
        total += _write_json(detail_dir / f"{c.clump_id}.json", detail)
        detail_count += 1

    # Separations — mirrors the /separations endpoint. Absent when no WCS.
    coords = clumps.centroid_skycoords()
    if coords is not None:
        clump_list = clumps.list_clumps()
        pairs: list[ClumpSeparation] = []
        n = len(clump_list)
        for i in range(n):
            a = clump_list[i]
            if a.ra_deg is None or a.dec_deg is None:
                continue
            for j in range(i + 1, n):
                bcl = clump_list[j]
                if bcl.ra_deg is None or bcl.dec_deg is None:
                    continue
                sep = skycoord_separation_arcsec(coords[i], coords[j])
                if not np.isfinite(sep):
                    continue
                pairs.append(
                    ClumpSeparation(
                        clump_a=a.clump_id,
                        clump_b=bcl.clump_id,
                        sep_arcsec=float(sep),
                        sep_pc=None,
                    )
                )
        total += _write_json(
            out / dataset / "separations.json",
            ClumpSeparationsResponse(distance_mpc=None, pairs=pairs).model_dump(mode="json"),
        )

    # Pixel-index grid: ny * nx int16, gzipped. Client indexes as [y*nx + x].
    grid = clumps._clump_map.astype(np.int16, copy=False)
    header = np.array([grid.shape[0], grid.shape[1]], dtype=np.int32).tobytes()
    out_path = out / dataset / "pixel_index.bin.gz"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wb", compresslevel=6) as fh:
        fh.write(header)
        fh.write(grid.tobytes(order="C"))
    total += out_path.stat().st_size

    return detail_count, total


def _bake_meta(
    out: Path,
    dataset: str,
    cubes: dict[str, DataCube],
    rgb_by_cube: dict[str, list[dict[str, Any]]],
) -> int:
    payload: dict[str, Any] = {
        "datacubes": list(cubes.keys()),
        "filters": {
            name: [
                FilterInfo(
                    index=i,
                    name=fname,
                    wavelength=NIRCAM_WAVELENGTHS.get(fname, 0.0),
                ).model_dump(mode="json")
                for i, fname in enumerate(dc.filter_names)
            ]
            for name, dc in cubes.items()
        },
        "rgb_presets": rgb_by_cube,
        "stretches": STRETCHES,
    }
    return _write_json(out / dataset / "meta.json", payload)


def _bake_manifest(out: Path, store: DataStore) -> int:
    payload = {
        "datasets": store.list_datasets(),
        "default": store.default_dataset,
        "wavelengths": NIRCAM_WAVELENGTHS,
        "stretches": STRETCHES,
        "rgb_presets": [list(p) for p in RGB_PRESETS],
    }
    return _write_json(out / "manifest.json", payload)


def bake(data_dir: Path, out_dir: Path) -> BakeStats:
    DataStore.reset()
    store = DataStore.get(JellyscopeConfig(data_dir=data_dir))

    out_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = _bake_manifest(out_dir, store)

    viewer_count = 0
    rgb_count = 0
    detail_count = 0

    for name in store.list_datasets():
        ds = store.get_dataset(name)
        assert ds.clumps is not None  # DataStore filters out clump-less dirs.
        rgb_by_cube: dict[str, list[dict[str, Any]]] = {}
        for cube_name, dc in ds.datacubes.items():
            vc, vb = _bake_viewer(out_dir, name, cube_name, dc, ds.clumps)
            re, rc, rb = _bake_rgb(out_dir, name, cube_name, dc, ds.clumps)
            viewer_count += vc
            rgb_count += rc
            total_bytes += vb + rb
            rgb_by_cube[cube_name] = re
        dc_meta_bytes = _bake_meta(out_dir, name, ds.datacubes, rgb_by_cube)
        dc_count, clump_bytes = _bake_clumps(out_dir, name, ds.clumps)
        detail_count += dc_count
        total_bytes += dc_meta_bytes + clump_bytes
        logger.info("baked %s: %d channels, %d rgb, %d clumps", name, vc, rc, dc_count)

    return BakeStats(
        datasets=len(store.list_datasets()),
        viewer_figures=viewer_count,
        rgb_figures=rgb_count,
        clump_details=detail_count,
        bytes_written=total_bytes,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--out", type=Path, default=Path("docs/data"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    stats = bake(args.data, args.out)
    print(
        f"prebake OK — {stats.datasets} datasets, {stats.viewer_figures} viewer + "
        f"{stats.rgb_figures} rgb figures, {stats.clump_details} clump details, "
        f"{stats.bytes_written / (1024 * 1024):.1f} MB written to {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
