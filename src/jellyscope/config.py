"""Application configuration."""

from pathlib import Path

from pydantic import BaseModel, Field

# JWST NIRCam filter central wavelengths in microns.
# https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-instrumentation/nircam-filters
NIRCAM_WAVELENGTHS: dict[str, float] = {
    "F070W": 0.704,
    "F090W": 0.901,
    "F115W": 1.154,
    "F140M": 1.404,
    "F150W": 1.501,
    "F162M": 1.627,
    "F182M": 1.845,
    "F200W": 1.990,
    "F210M": 2.093,
    "F250M": 2.503,
    "F277W": 2.786,
    "F300M": 2.996,
    "F335M": 3.365,
    "F356W": 3.563,
    "F360M": 3.621,
    "F410M": 4.092,
    "F430M": 4.280,
    "F444W": 4.421,
    "F460M": 4.624,
    "F480M": 4.834,
}

# Default RGB filter assignment.
DEFAULT_RGB: dict[str, str] = {"r": "F200W", "g": "F115W", "b": "F090W"}


class JellyscopeConfig(BaseModel):
    """Configuration for the Jellyscope application.

    The data_dir can point to a flat directory
    or contain subdirectories for multiple datasets.
    """

    data_dir: Path = Field(default_factory=lambda: Path("data"))
    datacube_file: str = "cut_datacube_nircam.fits"
    datacube_matched_file: str = "cut_datacube_nircam_matched.fits"
    clumps_properties_file: str = "clumps_properties.csv"
    clumps_pixels_file: str = "clumps_pixels.csv"
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = True
    default_colorscale: str = "Viridis"
    filter_wavelengths: dict[str, float] = Field(default_factory=lambda: dict(NIRCAM_WAVELENGTHS))
