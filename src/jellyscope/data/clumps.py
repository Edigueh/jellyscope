"""Clump catalog: properties, pixel masks, and boundaries."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull


@dataclass
class ClumpProperties:
    """Physical properties of a single detected clump."""

    clump_id: int
    area_pix: int
    area_arcsec2: float
    r_eff_arcsec: float
    x0: float
    y0: float
    area_kpc2: float
    r_eff_kpc: float
    inside: bool
    component: str


class ClumpCatalog:
    """Manages the clump catalog: properties, pixel masks, and boundaries.

    Dimensions are inferred from the datacube shape, not hardcoded.
    """

    def __init__(
        self,
        properties_path: Path | str,
        pixels_path: Path | str,
        spatial_shape: tuple[int, int],
    ) -> None:
        self.ny, self.nx = spatial_shape

        props_df = pd.read_csv(properties_path)
        self.clumps: dict[int, ClumpProperties] = {}
        for _, row in props_df.iterrows():
            cid = int(row["clump_id"])
            self.clumps[cid] = ClumpProperties(
                clump_id=cid,
                area_pix=int(row["area_pix"]),
                area_arcsec2=float(row["area_arcsec2"]),
                r_eff_arcsec=float(row["r_eff_arcsec"]),
                x0=float(row["x0"]),
                y0=float(row["y0"]),
                area_kpc2=float(row["area_kpc2"]),
                r_eff_kpc=float(row["r_eff_kpc"]),
                inside=bool(row["inside"]),
                component=str(row["component"]),
            )

        pixels_df = pd.read_csv(pixels_path)
        self._pixel_masks: dict[int, np.ndarray] = {}
        self._clump_map = np.full((self.ny, self.nx), -1, dtype=np.int32)

        for cid in self.clumps:
            mask = np.zeros((self.ny, self.nx), dtype=bool)
            cpx = pixels_df[pixels_df["clump_id"] == cid]
            for _, px in cpx.iterrows():
                x, y = int(px["x"]), int(px["y"])
                if 0 <= y < self.ny and 0 <= x < self.nx:
                    mask[y, x] = True
                    self._clump_map[y, x] = cid
            self._pixel_masks[cid] = mask

        self._boundaries: dict[int, list[tuple[int, int]]] = {}

    def get_clump(self, clump_id: int) -> ClumpProperties:
        return self.clumps[clump_id]

    def get_pixel_mask(self, clump_id: int) -> np.ndarray:
        return self._pixel_masks[clump_id]

    def get_combined_mask(self, clump_ids: list[int]) -> np.ndarray:
        """OR together masks for multiple clumps."""
        mask = np.zeros((self.ny, self.nx), dtype=bool)
        for cid in clump_ids:
            mask |= self._pixel_masks[cid]
        return mask

    def get_clump_at_pixel(self, x: int, y: int) -> int | None:
        """Return clump_id at pixel, or None if no clump there."""
        if 0 <= y < self.ny and 0 <= x < self.nx:
            val = self._clump_map[y, x]
            return int(val) if val >= 0 else None
        return None

    def get_boundary_coords(self, clump_id: int) -> list[tuple[float, float]]:
        """Return ordered boundary coordinates for a clump contour.

        Uses ConvexHull for clean polygon outlines. Returns pixel coords
        as (x, y) tuples forming a closed polygon.
        """
        if clump_id in self._boundaries:
            return self._boundaries[clump_id]

        mask = self._pixel_masks[clump_id]
        ys, xs = np.where(mask)

        if len(xs) < 3:
            coords = list(zip(xs.astype(float), ys.astype(float)))
            coords.append(coords[0])
            self._boundaries[clump_id] = coords
            return coords

        points = np.column_stack([xs, ys])
        try:
            hull = ConvexHull(points)
            verts = hull.vertices
            coords = [(float(points[v, 0]), float(points[v, 1])) for v in verts]
            coords.append(coords[0])
        except Exception:
            coords = list(zip(xs.astype(float), ys.astype(float)))
            coords.append(coords[0])

        self._boundaries[clump_id] = coords
        return coords

    def get_all_boundaries(self) -> dict[int, list[tuple[float, float]]]:
        return {cid: self.get_boundary_coords(cid) for cid in self.clumps}

    def list_clumps(self) -> list[ClumpProperties]:
        return list(self.clumps.values())

    def filter_clumps(
        self,
        component: str | None = None,
        inside: bool | None = None,
    ) -> list[ClumpProperties]:
        result = self.list_clumps()
        if component is not None:
            result = [c for c in result if c.component == component]
        if inside is not None:
            result = [c for c in result if c.inside == inside]
        return result

    def to_properties_list(self) -> list[dict]:
        """Return all clump properties as a list of dicts for JSON serialization."""
        return [
            {
                "clump_id": c.clump_id,
                "area_pix": c.area_pix,
                "area_arcsec2": round(c.area_arcsec2, 6),
                "r_eff_arcsec": round(c.r_eff_arcsec, 4),
                "x0": round(c.x0, 2),
                "y0": round(c.y0, 2),
                "area_kpc2": round(c.area_kpc2, 4),
                "r_eff_kpc": round(c.r_eff_kpc, 4),
                "inside": c.inside,
                "component": c.component,
            }
            for c in self.list_clumps()
        ]
