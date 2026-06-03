"""
Clump Catalog Module
--------------------
Handles the representation, spatial mapping, and geometric boundaries
of detected clumps (e.g., star-forming regions in a galaxy).
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from pydantic import BaseModel
from scipy.spatial import ConvexHull, QhullError

from jellyscope.data.model.coordinates import pixel_to_skycoord

logger = logging.getLogger(__name__)


class ClumpProperties(BaseModel):
    """
    Container for the physical and geometric metadata of a single clump.

    Attributes:
        clump_id: Unique identifier for the detection.
        area_pix: Total number of pixels belonging to the clump.
        area_arcsec2: Physical area in square arcseconds.
        r_eff_arcsec: Effective radius (half-light or geometric) in arcseconds.
        x0, y0: Centroid coordinates in the pixel grid.
        area_kpc2: Physical area in square kiloparsecs (cosmology-dependent).
        r_eff_kpc: Effective radius in kiloparsecs.
        inside: Boolean flag (e.g., if the clump is within a specific galactic radius).
        component: Structural classification (e.g., 'disk', 'bulge', 'outlier').
        ra_deg, dec_deg: Centroid sky coordinates in degrees. Populated by
            ``ClumpCatalog.attach_skycoords`` when a celestial WCS is available;
            ``None`` otherwise.
    """

    clump_id: int
    area_pix: int
    area_arcsec2: float
    r_eff_arcsec: float
    x0: float
    y0: float
    area_kpc2: float
    r_eff_kpc2: float
    inside: bool
    component: str
    ra_deg: float | None = None
    dec_deg: float | None = None


class ClumpCatalog:
    """Manages the clump catalog: properties, pixel masks and boundaries."""

    def __init__(
        self,
        properties_path: Path | str,
        pixels_path: Path | str,
        spatial_shape: tuple[int, int],
    ) -> None:
        """Initializes the catalog by loading CSV data and pre-computing spatial maps.

        Args:
            properties_path: Path to CSV containing ClumpProperties data.
            pixels_path: Path to CSV containing pixel-by-pixel assignments (clump_id, x, y).
            spatial_shape: The (height, width) of the original observation/datacube.
        """
        self.shape: tuple[int, int] = spatial_shape
        self.ny, self.nx = spatial_shape
        self.CLUMP_ID_KEY: str = "clump_id"
        self.AREA_PIX_KEY: str = "area_pix"
        self.AREA_ARCSEC2_KEY: str = "area_arcsec2"
        self.R_EFF_ARCSEC_KEY: str = "r_eff_arcsec"
        self.X0_KEY: str = "x0"
        self.Y0_KEY: str = "y0"
        self.AREA_KPC2_KEY: str = "area_kpc2"
        self.R_EFF_KPC2_KEY: str = "r_eff_kpc"
        self.INSIDE_KEY: str = "inside"
        self.COMPONENT_KEY: str = "component"

        # 1. Load summary properties
        props_df = pd.read_csv(properties_path)
        self.clumps: dict[int, ClumpProperties] = {}
        for _, row in props_df.iterrows():
            cid = int(row[self.CLUMP_ID_KEY])
            self.clumps[cid] = ClumpProperties(
                clump_id=cid,
                area_pix=int(row[self.AREA_PIX_KEY]),
                area_arcsec2=float(row[self.AREA_ARCSEC2_KEY]),
                r_eff_arcsec=float(row[self.R_EFF_ARCSEC_KEY]),
                x0=float(row[self.X0_KEY]),
                y0=float(row[self.Y0_KEY]),
                area_kpc2=float(row[self.AREA_KPC2_KEY]),
                r_eff_kpc2=float(row[self.R_EFF_KPC2_KEY]),
                inside=bool(row[self.INSIDE_KEY]),
                component=str(row[self.COMPONENT_KEY]),
            )

        # 2. Load and map pixel-level data
        pixels_df = pd.read_csv(pixels_path)
        self._pixels_masks: dict[int, np.ndarray] = {}
        # _clump_map is a 2D grid where each cell contains the ID of the clump occupying it.
        self._clump_map = np.full(spatial_shape, -1, dtype=np.int32)

        for cid in self.clumps:
            # Create a boolean mask for each individual clump for fast logical operations.
            mask = np.zeros(spatial_shape, dtype=bool)
            clump_pixels = pixels_df[pixels_df[self.CLUMP_ID_KEY] == cid]
            for _, px in clump_pixels.iterrows():
                x, y = int(px["x"]), int(px["y"])
                if self._is_coordinate_in_bounds(x, y):
                    mask[y, x] = True
                    self._clump_map[y, x] = cid

            self._pixels_masks[cid] = mask

        # Lazy-loaded cache for geometric boundaries
        self._boundaries: dict[int, list[tuple[float, float]]] = {}

        # Populated by ``attach_skycoords`` when a celestial WCS is available.
        self._centroid_skycoords: SkyCoord | None = None

    def _is_coordinate_in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.nx and 0 <= y < self.ny

    def get_clump_by_id(self, clump_id: int) -> ClumpProperties:
        """Fetch the property dataclass for a specific ID."""
        return self.clumps[clump_id]

    def get_pixel_mask(self, clump_id: int) -> np.ndarray:
        """Get a 2D boolean array where True represents the clump area."""
        return self._pixels_masks[clump_id]

    def get_combined_mask(self, clump_ids: list[int]) -> np.ndarray:
        """Merges multiple clumps into a single boolean mask using bitwise OR."""
        mask = np.zeros(self.shape, dtype=bool)
        for cid in clump_ids:
            mask |= self._pixels_masks[cid]
        return mask

    def get_clump_id_at_pixel(self, x: int, y: int) -> int | None:
        """Return clump id at the given pixel, or None if no clump is set there."""
        if self._is_coordinate_in_bounds(x, y):
            val = self._clump_map[y, x]
            return int(val) if val >= 0 else None
        return None

    def get_boundary_coords(self, clump_id: int) -> list[tuple[float, float]]:
        """Calculates the outer boundary of a clump for plotting or region selection.

        Uses ConvexHull for clean polygon outlines.
        Returns pixel coords as tuple(x, y) forming a closed polygon.
        """
        # Return cached boundary if already computed
        if clump_id in self._boundaries:
            return self._boundaries[clump_id]

        mask = self._pixels_masks[clump_id]
        ys, xs = np.where(mask)

        # Handle edge case: small clumps cannot form a hull
        if len(xs) < 3:
            coords = list(zip(xs.astype(float), ys.astype(float), strict=True))
            coords.append(coords[0])  # Close the loop in the graph, making it cyclic.
            self._boundaries[clump_id] = coords
            return coords

        points = np.column_stack([xs, ys])
        try:
            # https://www.geeksforgeeks.org/dsa/convex-hull-algorithm/
            hull = ConvexHull(points)  # smallest convex polygon that encloses all of the points.
            verts = hull.vertices

            # verts contains indices of points on the outer edge.
            # Interior points are excluded. Look up each index in the points
            # array to get the actual (x, y) coordinates for the boundary polygon.
            coords = [(float(points[v, 0]), float(points[v, 1])) for v in verts]
            coords.append(coords[0])
        except QhullError:
            # If points are colinear or hull generation fails.
            coords = list(zip(xs.astype(float), ys.astype(float), strict=True))
            coords.append(coords[0])

        self._boundaries[clump_id] = coords
        return coords

    def get_all_boundaries(self) -> dict[int, list[tuple[float, float]]]:
        """Pre-calculates or retrieves boundaries for every clump in the catalog."""
        return {cid: self.get_boundary_coords(cid) for cid in self.clumps}

    def list_clumps(self) -> list[ClumpProperties]:
        """Returns all clump objects as a flat list."""
        return list(self.clumps.values())

    def filter_clumps(
        self,
        component: str | None = None,
        inside: bool | None = None,
    ) -> list[ClumpProperties]:
        """
        Search the catalog based on specific metadata attributes.

        Example: catalog.filter_clumps(component='disk', inside=True)
        """
        filtered_clump_list = self.list_clumps()
        if component is not None:
            filtered_clump_list = [c for c in filtered_clump_list if c.component == component]
        if inside is not None:
            filtered_clump_list = [c for c in filtered_clump_list if c.inside == inside]
        return filtered_clump_list

    def attach_skycoords(self, wcs: WCS) -> None:
        """Compute and cache RA/Dec for every clump centroid using ``wcs``.

        Uses ``pixel_to_skycoord`` for the projection so all sky-coordinate
        logic stays in one module. The resulting SkyCoord vector is cached on
        ``self._centroid_skycoords`` for the pairwise-separations endpoint.
        """
        clump_list = self.list_clumps()
        if not clump_list:
            self._centroid_skycoords = None
            return

        xs = np.array([c.x0 for c in clump_list], dtype=np.float64)
        ys = np.array([c.y0 for c in clump_list], dtype=np.float64)
        try:
            coords: SkyCoord = pixel_to_skycoord(xs, ys, wcs)
        except Exception:  # pragma: no cover - astropy edge case
            logger.exception("attach_skycoords: pixel_to_world failed")
            self._centroid_skycoords = None
            return

        ra_arr = np.asarray(coords.ra.deg, dtype=np.float64)
        dec_arr = np.asarray(coords.dec.deg, dtype=np.float64)
        for c, ra, dec in zip(clump_list, ra_arr, dec_arr, strict=True):
            c.ra_deg = float(ra) if np.isfinite(ra) else None
            c.dec_deg = float(dec) if np.isfinite(dec) else None

        self._centroid_skycoords = coords

    def centroid_skycoords(self) -> SkyCoord | None:
        """Return cached centroid SkyCoord vector, or None if WCS unavailable."""
        return self._centroid_skycoords

    def to_properties_list(self) -> list[dict[str, Any]]:
        """Return all clump properties as a list of dicts for JSON serialization."""
        return [
            {
                self.CLUMP_ID_KEY: c.clump_id,
                self.AREA_PIX_KEY: c.area_pix,
                self.AREA_ARCSEC2_KEY: c.area_arcsec2,
                self.R_EFF_ARCSEC_KEY: c.r_eff_arcsec,
                self.X0_KEY: c.x0,
                self.Y0_KEY: c.y0,
                self.AREA_KPC2_KEY: c.area_kpc2,
                self.R_EFF_KPC2_KEY: c.r_eff_kpc2,
                self.INSIDE_KEY: c.inside,
                self.COMPONENT_KEY: c.component,
                "ra_deg": c.ra_deg,
                "dec_deg": c.dec_deg,
            }
            for c in self.list_clumps()
        ]
