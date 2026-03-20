"""Clumps catalog: properties, pixel masks and boundaries."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, QhullError


@dataclass
class ClumpProperties:
    """Physical properties of a single detected clump."""

    clump_id: int
    area_pix: int
    area_arcsec2: float
    r_eff_arcesc: float
    x0: float
    y0: float
    area_kpc2: float
    r_eff_kpc2: float
    inside: bool # ?
    component: str # ?


class ClumpCatalog:
    """Manages the clump catalog: properties, pixel masks and boundaries."""

    def __init__(
        self,
        properties_path: Path | str,
        pixels_path: Path | str,
        spatial_shape: tuple[int, int],
    ) -> None:
        self.shape: tuple[int, int] = spatial_shape
        self.ny, self.nx = spatial_shape
        self.CLUMP_ID_KEY: str = "clump_id"
        self.AREA_PIX_KEY: str = "area_pix"
        self.AREA_ARCSEC2_KEY: str = "area_arcsec2"
        self.R_EFF_ARCESC_KEY: str = "r_eff_arcesc"
        self.X0_KEY: str = "x0"
        self.Y0_KEY: str = "y0"
        self.AREA_KPC2_KEY: str = "area_kpc2"
        self.R_EFF_KPC2_KEY: str = "r_eff_kpc2"
        self.INSIDE_KEY: str = "inside"
        self.COMPONENT_KEY: str = "component"

        props_df = pd.read_csv(properties_path)
        self.clumps: dict[int, ClumpProperties] = {}
        for _, row in props_df.iterrows():
            cid = int(row[self.CLUMP_ID_KEY])
            self.clumps[cid] = ClumpProperties(
                clump_id=cid,
                area_pix=int(row[self.AREA_PIX_KEY]),
                area_arcsec2=float(row[self.AREA_ARCSEC2_KEY]),
                r_eff_arcesc=float(row[self.R_EFF_ARCESC_KEY]),
                x0=float(row[self.X0_KEY]),
                y0=float(row[self.Y0_KEY]),
                area_kpc2=float(row[self.AREA_KPC2_KEY]),
                r_eff_kpc2=float(row[self.R_EFF_KPC2_KEY]),
                inside=bool(row[self.INSIDE_KEY]),
                component=str(row[self.COMPONENT_KEY]),
            )

        pixels_df = pd.read_csv(pixels_path)
        self._pixels_masks: dict[int, np.ndarray] = {}
        self._clump_map = np.full(spatial_shape, -1, dtype=np.int32)

        for cid in self.clumps:
            mask = np.zeros(spatial_shape, dtype=bool)
            clump_pixels = pixels_df[pixels_df[self.CLUMP_ID_KEY] == cid]
            for _, px in clump_pixels.iterrows():
                x, y = int(px["x"]), int(px["y"])
                if self._is_coordinate_in_bounds(x, y):
                    mask[y, x] = True
                    self._clump_map[y, x] = cid

            self._pixels_masks[cid] = mask

        self._boundaries: dict[int, list[tuple[float, float]]] = {}

    def _is_coordinate_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.nx and 0 <= y < self.ny

    def get_clump_by_id(self, clump_id: int) -> ClumpProperties:
        return self.clumps[clump_id]

    def get_pixel_mask(self, clump_id: int) -> np.ndarray:
        return self._pixels_masks[clump_id]

    def get_combined_masks(self, clump_ids: list[int]) -> np.ndarray:
        """Groups multiple clumps together."""
        mask = np.zeros(self.shape, dtype=bool)
        for cid in clump_ids:
            mask |= self._pixels_masks[cid]
        return mask

    def get_clump_id_at_pixel(self, x: int, y: int) -> int | None:
        """Return clump id at the given pixel, or None if not found."""
        if self._is_coordinate_in_bounds(x, y):
            val = self._clump_map[y, x]
            return int(val) if val >= 0 else None
        return None 
    