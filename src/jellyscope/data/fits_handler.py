"""FITS datacube I/O and slicing."""

from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


class DataCube:
    """Manages a 3D FITS datacube (filter, y, x).

    Reads all metadata (filter names, WCS, dimensions) from the FITS header,
    so it works with any datacube without hardcoded assumptions.
    """

    def __init__(self, filepath: Path | str) -> None:
        filepath = Path(filepath)
        with fits.open(filepath) as hdul:
            self.data: np.ndarray = hdul[0].data.astype(np.float64)
            self.header = hdul[0].header
            self.wcs = WCS(self.header, naxis=2)

        self.n_channels, self.ny, self.nx = self.data.shape
        self.filter_names = self._read_filter_names()
        self.name = filepath.stem

    def _read_filter_names(self) -> list[str]:
        """Read filter names from FITS header keys FILTER1..FILTERn."""
        names = []
        for i in range(1, self.n_channels + 1):
            key = f"FILTER{i}"
            if key in self.header:
                names.append(str(self.header[key]))
            else:
                names.append(f"CH{i}")
        return names

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.data.shape

    @property
    def spatial_shape(self) -> tuple[int, int]:
        return (self.ny, self.nx)

    def get_slice(self, channel_index: int) -> np.ndarray:
        """Return 2D array (ny, nx) for a single filter channel."""
        if not 0 <= channel_index < self.n_channels:
            raise IndexError(f"Channel index {channel_index} out of range [0, {self.n_channels})")
        return np.asarray(self.data[channel_index])

    def get_slice_by_name(self, filter_name: str) -> np.ndarray:
        """Return 2D slice by filter name (e.g., 'F200W')."""
        idx = self.filter_names.index(filter_name)
        return self.get_slice(idx)

    def get_spectrum_at_pixel(self, x: int, y: int) -> np.ndarray:
        """Return 1D array of length n_channels for a single spatial pixel."""
        return self.data[:, y, x].copy()

    def get_mean_spectrum_for_mask(self, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute mean and std spectrum across masked pixels.

        Args:
            mask: Boolean 2D array (ny, nx).

        Returns:
            Tuple of (mean_spectrum, std_spectrum), each 1D with n_channels elements.
        """
        pixels = self.data[:, mask]  # shape: (n_channels, n_pixels)
        mean = np.nanmean(pixels, axis=1)
        std = np.nanstd(pixels, axis=1)
        return mean, std

    def to_json_slice(self, channel_index: int) -> list[list[float | None]]:
        """Return a 2D slice as nested lists, with NaN replaced by None for Plotly."""
        arr = self.get_slice(channel_index)
        result = []
        for row in arr:
            result.append([None if np.isnan(v) else float(v) for v in row])
        return result
