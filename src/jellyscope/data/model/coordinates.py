"""Coordinate utilities: pixel <-> sky coordinates and angular separations.

Pure helpers over ``astropy.wcs.WCS``. No I/O, no Plotly. Lives next to the
``DataCube`` and ``ClumpCatalog`` models because pixel↔sky conversion is a
derivation step over the data those models hold.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS


class ImageAxisBounds(TypedDict):
    """FOV bounds and min-span for an image figure's axes."""

    x: tuple[float, float]
    y: tuple[float, float]
    x_min_span: float
    y_min_span: float


def pixel_to_skycoord(x: float | np.ndarray, y: float | np.ndarray, wcs: WCS) -> SkyCoord:
    """Convert pixel coordinates to a SkyCoord (RA/Dec).

    Args:
        x, y: Pixel coordinates (0-based). Can be scalars or arrays.
        wcs: Astropy WCS object with celestial axes.

    Returns:
        SkyCoord with the same shape as the inputs.
    """
    return wcs.pixel_to_world(x, y)


def pixels_to_radec_arrays(
    xs: np.ndarray | list[float],
    ys: np.ndarray | list[float],
    wcs: WCS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized pixel→RA/Dec for plotting and bulk catalog tasks.

    Calls ``pixel_to_skycoord`` once for the full input, pulls the RA/Dec
    arrays out of the resulting SkyCoord, and returns a finite mask so
    callers can decide how to render or skip degenerate vertices.

    Args:
        xs, ys: Pixel coordinates (0-based). Scalars are lifted to length-1
            arrays so the return shape is always 1-D.
        wcs: Astropy WCS with celestial axes.

    Returns:
        ``(ra_deg, dec_deg, finite_mask)`` — three NumPy arrays of equal
        length. ``finite_mask`` is True where both RA and Dec are finite.
    """
    xs_arr = np.atleast_1d(np.asarray(xs, dtype=np.float64))
    ys_arr = np.atleast_1d(np.asarray(ys, dtype=np.float64))
    sky = pixel_to_skycoord(xs_arr, ys_arr, wcs)
    ra = np.asarray(sky.ra.deg, dtype=np.float64)
    dec = np.asarray(sky.dec.deg, dtype=np.float64)
    finite = np.isfinite(ra) & np.isfinite(dec)
    return ra, dec, finite


def skycoord_separation_arcsec(c1: SkyCoord, c2: SkyCoord) -> float:
    """Great-circle angular separation between two SkyCoord points in arcsec."""
    return float(c1.separation(c2).to(u.arcsec).value)


def pixel_scale_arcsec(wcs: WCS) -> float:
    """Mean linear pixel scale in arcsec/pixel.

    Useful for option A (parsec axes) once a galaxy distance is configured.
    """
    pscale = wcs.proj_plane_pixel_scales()
    values = u.Quantity(pscale).to(u.arcsec).value
    return float(np.mean(values))


def arcsec_axis(n: int, arcsec_per_pix: float) -> np.ndarray:
    """Axis values for an n-cell axis in arcsec, centered on image center.

    Cell ``i`` (0-based) maps to ``(i - (n - 1)/2) * arcsec_per_pix``. For odd
    ``n``, cell ``(n-1)/2`` is exactly 0; for even ``n``, the axis straddles 0
    by half a cell. Use this for Plotly heatmap ``x``/``y`` arrays.
    """
    ref = (n - 1) / 2.0
    return (np.arange(n, dtype=np.float64) - ref) * arcsec_per_pix


def image_arcsec_extent(nx: int, ny: int, arcsec_per_pix: float) -> dict[str, float]:
    """Image-extent kwargs (``x``, ``y``, ``sizex``, ``sizey``) for
    ``layout.images[]`` so a PNG image overlay aligns with the centered
    arcsec axes produced by :func:`arcsec_axis`.
    """
    return {
        "x": -nx * arcsec_per_pix / 2.0,
        "y": -ny * arcsec_per_pix / 2.0,
        "sizex": nx * arcsec_per_pix,
        "sizey": ny * arcsec_per_pix,
    }


def image_axis_bounds(
    nx: int,
    ny: int,
    arcsec_per_pix: float | None,
    min_span_pixels: int = 5,
) -> ImageAxisBounds:
    """Axis bounds and min-span for the image FOV.

    Returns a dict with:
    - ``"x"``, ``"y"``: ``(min, max)`` tuples for the axis range.
    - ``"x_min_span"``, ``"y_min_span"``: minimum allowed visible span in
      axis units (``min_span_pixels`` * pixel scale). Used by the
      front-end zoom handler to floor the zoom-in level so users do not
      zoom past the underlying pixel resolution.

    When ``arcsec_per_pix`` is provided, bounds match the centered arcsec axes
    produced by :func:`arcsec_axis` / :func:`image_arcsec_extent`. When it is
    ``None`` (no celestial WCS), bounds fall back to pixel coordinates
    ``[0, nx]`` and ``[0, ny]``; the min-span is then in raw pixels.
    """
    unit = arcsec_per_pix if arcsec_per_pix is not None else 1.0
    min_span = float(min_span_pixels) * unit

    if arcsec_per_pix is not None:
        ext = image_arcsec_extent(nx, ny, arcsec_per_pix)
        x_bounds = (ext["x"], ext["x"] + ext["sizex"])
        y_bounds = (ext["y"], ext["y"] + ext["sizey"])
    else:
        x_bounds = (0.0, float(nx))
        y_bounds = (0.0, float(ny))

    return {
        "x": x_bounds,
        "y": y_bounds,
        "x_min_span": min_span,
        "y_min_span": min_span,
    }
