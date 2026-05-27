"""FITS datacube I/O and slicing."""

from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS  # Handles "World Coordinate System" (mapping pixels to space)


class DataCube:
    """ "Manages a 3D FITS datacube (filter, y, x).

    Reads all metadata (filters, WCS, dimensions) from the FITS file header.
    FITS = (Flexible Image Transport System).
    """

    def __init__(self, filepath: Path | str) -> None:
        filepath = Path(filepath)
        with fits.open(filepath) as hdul:
            # Extracts the raw pixel data and converts to float64 for precision.
            self.data: np.ndarray = np.ascontiguousarray(hdul[0].data, dtype=np.float64)
            # The header contains metadata such as telescope name, exposure time...
            self.header = hdul[0].header
            # Initializes the WCS to map (x, y) to celestial coordinates.
            self.wcs = WCS(self.header, naxis=2)

        self.n_channels, self.ny, self.nx = self.data.shape
        self.filter_names = self._read_filter_names()
        self.name = filepath.stem

    def _read_filter_names(self) -> list[str]:
        """Read filter names from FITS header keys FILTER11...FILTERn."""
        names: list[str] = []
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

    def get_slice_by_channel_index(self, channel_index: int) -> np.ndarray:
        """Return 2D array (ny, nx) for a single filter channel."""
        if not 0 <= channel_index < self.n_channels:
            raise IndexError(f"Channel index {channel_index} out of range [0, {self.n_channels})")
        slice_: np.ndarray = self.data[channel_index]
        return slice_

    def get_slice_by_name(self, filter_name: str) -> np.ndarray:
        """Return 2D slice by filter name (e.g., 'F200W')"""
        return self.get_slice_by_channel_index(self.filter_names.index(filter_name))

    def get_spectrum_at_pixel(self, x: int, y: int) -> np.ndarray:
        """Return 1D array of length n_channels for a single spaxel."""
        # This returns all wavelengths (deepness) for a single spaxel.
        return self.data[:, y, x].copy()

    def get_mean_spectrum_for_mask(self, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute mean and std spectrum across masked pixels.

        Args:
            mask: Boolean 2D array (ny, nx).

        Returns:
            Tuple of (mean_spectrum, std_spectrum), each 1D with n_channels elements.
        """
        pixels = self.data[:, mask]  # Returns the pixels where the mask is True.
        # Calculate average and standard deviation, ignoring NaN values.
        mean = np.nanmean(pixels, axis=1)
        std = np.nanstd(pixels, axis=1)
        return mean, std

    def to_json_slice(self, channel_index: int) -> list[list[float | None]]:
        """Return a 2D slice as nested lists, with NaN replaced by None for Plotly."""
        arr = self.get_slice_by_channel_index(channel_index)
        out = arr.astype(object)
        out[np.isnan(arr)] = None
        result: list[list[float | None]] = out.tolist()
        return result
