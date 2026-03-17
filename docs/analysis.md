# Analysis Layer

The analysis layer extracts scientific information from the raw datacube data. It sits between the data layer (which handles I/O) and the visualization layer (which builds Plotly figures). All functions are pure — they take data objects as input and return plain Python dicts suitable for JSON serialization.

**Files covered**:

- [analysis/spectral.py](../src/jellyscope/analysis/spectral.py) — SED extraction
- [analysis/statistics.py](../src/jellyscope/analysis/statistics.py) — Region statistics

---

## analysis/spectral.py — Spectral Extraction

**Location**: `src/jellyscope/analysis/spectral.py`

This module extracts Spectral Energy Distributions (SEDs) from the datacube. An SED is the flux measured at each wavelength/filter for a given spatial region — it tells you how bright that region is at different wavelengths, which encodes physical information about temperature, dust, star formation, etc.

### Helper: `_wavelengths_for(filter_names: list[str]) -> list[float]`

Maps filter names to central wavelengths in microns using `NIRCAM_WAVELENGTHS` from config. Filters not found in the dictionary get `0.0`.

```python
_wavelengths_for(["F070W", "F200W"])  # → [0.704, 1.990]
```

---

### `extract_pixel_spectrum(datacube, x, y) -> dict`

Extracts the SED at a single spatial pixel.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | The loaded datacube |
| `x` | `int` | Pixel x coordinate |
| `y` | `int` | Pixel y coordinate |

**Returns**:

```python
{
    "filter_names": ["F070W", "F090W", ...],    # 20 filter names
    "wavelengths": [0.704, 0.901, ...],          # 20 wavelengths in microns
    "fluxes": [0.0123, 0.0456, ...],             # 20 flux values (None if NaN)
    "n_pixels": 1
}
```

**Usage**:

```python
from jellyscope.data.cache import DataStore
from jellyscope.analysis.spectral import extract_pixel_spectrum

store = DataStore.get()
dc = store.get_datacube("nircam")
spec = extract_pixel_spectrum(dc, 80, 100)
```

---

### `extract_clump_spectrum(datacube, clumps, clump_id) -> dict`

Computes the mean SED over all pixels belonging to a clump. Also returns the standard deviation per channel, which represents the pixel-to-pixel variation within the clump.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | The loaded datacube |
| `clumps` | `ClumpCatalog` | The clump catalog |
| `clump_id` | `int` | ID of the clump |

**Returns**:

```python
{
    "filter_names": ["F070W", "F090W", ...],
    "wavelengths": [0.704, 0.901, ...],
    "mean_flux": [0.0234, 0.0567, ...],    # Mean across clump pixels
    "std_flux": [0.0012, 0.0034, ...],     # Standard deviation
    "n_pixels": 144,                        # Number of pixels in clump
    "clump_id": 4
}
```

**How it works**:

1. Gets the boolean pixel mask for the clump via `clumps.get_pixel_mask(clump_id)`
2. Calls `datacube.get_mean_spectrum_for_mask(mask)` which computes `nanmean` and `nanstd` across all masked pixels for each channel
3. NaN values in the result are replaced with `None` for JSON compatibility

---

### `extract_region_spectrum(datacube, mask) -> dict`

Computes the mean SED for an arbitrary boolean mask. Used for lasso and rectangle selections drawn by the user.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | The loaded datacube |
| `mask` | `np.ndarray` | Boolean 2D array `(ny, nx)` |

**Returns**: Same format as `extract_clump_spectrum` (without `clump_id`).

**Edge case**: If the mask has zero `True` pixels, returns all `None` fluxes with `n_pixels: 0`.

**Usage**:

```python
import numpy as np
from jellyscope.analysis.spectral import extract_region_spectrum

# Create a rectangular region
mask = np.zeros((221, 172), dtype=bool)
mask[50:80, 60:100] = True
spec = extract_region_spectrum(dc, mask)
```

---

## analysis/statistics.py — Region Statistics

**Location**: `src/jellyscope/analysis/statistics.py`

Computes summary statistics for spatial regions at specific filter channels. Useful for characterizing how bright/variable a region is in a particular band.

### `compute_region_stats(datacube, mask, channel_index) -> dict`

Statistics for a spatial region at one filter channel.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | The loaded datacube |
| `mask` | `np.ndarray` | Boolean 2D array `(ny, nx)` |
| `channel_index` | `int` | Filter channel index `[0, n_channels)` |

**Returns**:

```python
{
    "filter": "F200W",
    "n_pixels": 144,
    "mean": 0.2345,
    "median": 0.2100,
    "std": 0.0567,
    "min": 0.0012,
    "max": 0.8901,
    "sum": 33.768
}
```

**Edge case**: If the mask has no valid (non-NaN) pixels, all numeric fields are `None`.

NaN pixels within the mask are excluded from calculations (filtered before `np.mean`, etc.).

---

### `compute_clump_summary(datacube, clumps, clump_id) -> dict`

Comprehensive summary combining clump physical properties with per-channel statistics.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | The loaded datacube |
| `clumps` | `ClumpCatalog` | The clump catalog |
| `clump_id` | `int` | ID of the clump |

**Returns**:

```python
{
    "clump_id": 4,
    "component": "disk",
    "area_pix": 144,
    "area_kpc2": 1.1165,
    "r_eff_kpc": 0.5961,
    "inside": True,
    "channel_stats": [
        {"filter": "F070W", "n_pixels": 144, "mean": 0.012, ...},
        {"filter": "F090W", "n_pixels": 144, "mean": 0.034, ...},
        # ... 20 entries total
    ]
}
```

This calls `compute_region_stats` for each of the 20 channels, providing a complete radiometric profile of the clump.
