# Data Layer

The data layer is the foundation of Jellyscope. It handles loading FITS datacubes, managing the clump catalog, and keeping everything cached in memory for fast access. All modules in this layer have zero dependencies on higher layers (visualization, web), so they can be used as standalone libraries.

**Files covered**:

- [config.py](../src/jellyscope/config.py) — Application configuration
- [data/data_store.py](../src/jellyscope/data/data_store.py) — Multi-dataset in-memory data store
- [data/model/datacube.py](../src/jellyscope/data/model/datacube.py) — FITS datacube I/O
- [data/model/clumps.py](../src/jellyscope/data/model/clumps.py) — Clump catalog management
- [model/schemas.py](../src/jellyscope/model/schemas.py) — Pydantic API request/response models
- [spec_analysis/spectral.py](../src/jellyscope/spec_analysis/spectral.py) — Pixel/clump/region spectrum extraction
- [spec_analysis/stats.py](../src/jellyscope/spec_analysis/stats.py) — Statistical helpers (currently unused)

---

## config.py — Application Configuration

**Location**: `src/jellyscope/config.py`

### `NIRCAM_WAVELENGTHS`

Module-level dictionary mapping JWST NIRCam filter names to their central wavelengths in microns.

```python
NIRCAM_WAVELENGTHS: dict[str, float] = {
    "F070W": 0.704,  "F090W": 0.901,  "F115W": 1.154,  "F140M": 1.404,
    "F150W": 1.501,  "F162M": 1.627,  "F182M": 1.845,  "F200W": 1.990,
    "F210M": 2.093,  "F250M": 2.503,  "F277W": 2.786,  "F300M": 2.996,
    "F335M": 3.365,  "F356W": 3.563,  "F360M": 3.621,  "F410M": 4.092,
    "F430M": 4.280,  "F444W": 4.421,  "F460M": 4.624,  "F480M": 4.834,
}
```

The naming convention (`F` + wavelength in nm + `W`/`M`) follows JWST standard: `W` = wide-band, `M` = medium-band.

### `DEFAULT_RGB`

Module-level dictionary defining the default filter assignments for the RGB composite view.

```python
DEFAULT_RGB: dict[str, str] = {"r": "F200W", "g": "F115W", "b": "F090W"}
```

These are the filters the frontend uses to seed the R/G/B dropdowns at startup (via `DEFAULT_RGB_FILTERS` in `app.js`, resolved to channel indices by `defaultRgbIndex()`). They satisfy the wavelength-ordering constraint λ_R > λ_G > λ_B that the UI enforces on user selections.

### `JellyscopeConfig`

Pydantic `BaseModel` holding all application settings. Every field has a sensible default, so `JellyscopeConfig()` works out of the box with the toy data.

```python
class JellyscopeConfig(BaseModel):
    data_dir: Path               # Root directory for data files (default: "data")
    datacube_file: str           # Primary datacube filename (default: "cut_datacube_nircam.fits")
    datacube_matched_file: str   # PSF-matched datacube (default: "cut_datacube_nircam_matched.fits")
    clumps_properties_file: str  # Clump properties CSV (default: "clumps_properties.csv")
    clumps_pixels_file: str      # Clump pixel coordinates CSV (default: "clumps_pixels.csv")
    host: str                    # Server host (default: "127.0.0.1")
    port: int                    # Server port (default: 5000)
    debug: bool                  # Debug mode (default: True)
    default_colorscale: str      # Plotly colorscale name (default: "Viridis")
    filter_wavelengths: dict[str, float]  # Filter → wavelength mapping (default: NIRCAM_WAVELENGTHS)
    enable_sed: bool             # Gate spectrum endpoints (default: False — SED routes return 404)
```

**Usage**:

```python
from jellyscope.config import JellyscopeConfig
from pathlib import Path

# Default config for toy data
config = JellyscopeConfig()

# Custom config for a different dataset
config = JellyscopeConfig(data_dir=Path("/data/galaxy_jw2736"))
```

---

## data/model/datacube.py — DataCube

**Location**: `src/jellyscope/data/model/datacube.py`

The `DataCube` class wraps a single 3D FITS file. It reads all metadata from the FITS header — nothing is hardcoded — so it works with any datacube that follows the `(n_channels, ny, nx)` shape convention with `FILTER1..FILTERn` header keys.

### Class: `DataCube`

#### `__init__(filepath: Path | str) -> None`

Opens the FITS file and loads data + metadata into memory.

```python
dc = DataCube("data/cut_datacube_nircam.fits")
```

**What happens internally**:

1. `astropy.io.fits.open(filepath)` reads the Primary HDU
2. `hdul[0].data` is cast to `float64` and stored in `self.data`
3. `hdul[0].header` is stored in `self.header`
4. `WCS(header, naxis=2)` creates a 2D World Coordinate System object for RA/DEC transformations
5. Shape is unpacked: `self.n_channels, self.ny, self.nx = self.data.shape`
6. Filter names are read from `FILTER1..FILTERn` header keys

**Attributes after init**:

| Attribute | Type | Example | Description |
| ----------- | ------ | --------- | ------------- |
| `data` | `np.ndarray` | shape `(20, 221, 172)` | The 3D datacube array |
| `header` | `astropy.io.fits.Header` | — | Full FITS header |
| `wcs` | `astropy.wcs.WCS` | — | 2D WCS for RA/DEC conversion |
| `n_channels` | `int` | `20` | Number of filter channels |
| `ny` | `int` | `221` | Spatial height in pixels |
| `nx` | `int` | `172` | Spatial width in pixels |
| `filter_names` | `list[str]` | `["F070W", "F090W", ...]` | Filter names from header |
| `name` | `str` | `"cut_datacube_nircam"` | Filename stem |

#### `_read_filter_names() -> list[str]`

**Private**. Reads `FILTER1`, `FILTER2`, ..., `FILTERn` from the FITS header. If a key is missing (non-standard FITS), falls back to `CH1`, `CH2`, etc.

#### `shape -> tuple[int, int, int]` (property)

Returns `(n_channels, ny, nx)`. Same as `self.data.shape`.

#### `spatial_shape -> tuple[int, int]` (property)

Returns `(ny, nx)`. Used when creating boolean masks of matching dimensions.

#### `get_slice_by_channel_index(channel_index: int) -> np.ndarray`

Returns a 2D array `(ny, nx)` for one filter channel.

```python
f200w_image = dc.get_slice_by_channel_index(7)  # F200W is channel index 7
print(f200w_image.shape)       # (221, 172)
```

**Raises**: `IndexError` if `channel_index` is out of `[0, n_channels)`.

#### `get_slice_by_name(filter_name: str) -> np.ndarray`

Same as `get_slice_by_channel_index()` but accepts a filter name string.

```python
image = dc.get_slice_by_name("F200W")
```

**Raises**: `ValueError` if `filter_name` not found in `filter_names`.

#### `get_spectrum_at_pixel(x: int, y: int) -> np.ndarray`

Returns a 1D array of length `n_channels` — the flux values at pixel `(x, y)` across all filters. This is the Spectral Energy Distribution (SED) of that pixel.

```python
sed = dc.get_spectrum_at_pixel(80, 100)
print(sed.shape)  # (20,)
```

**Note**: Array indexing is `data[:, y, x]` (FITS convention: axis 0 = channel, axis 1 = y, axis 2 = x).

#### `get_mean_spectrum_for_mask(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]`

Computes the mean and standard deviation spectrum across all `True` pixels in a boolean mask.

```python
mask = np.zeros((221, 172), dtype=bool)
mask[50:60, 70:80] = True  # 10x10 region
mean_spec, std_spec = dc.get_mean_spectrum_for_mask(mask)
# mean_spec.shape == (20,), std_spec.shape == (20,)
```

Uses `np.nanmean` and `np.nanstd` so that `NaN` pixels are ignored rather than propagated.

**Returns**: Tuple `(mean_spectrum, std_spectrum)`, each 1D with `n_channels` elements.

#### `to_json_slice(channel_index: int) -> list[list[float | None]]`

Returns a 2D slice as nested Python lists, suitable for JSON serialization. `NaN` values are replaced with `None` (which becomes `null` in JSON), so Plotly.js renders them as transparent gaps.

```python
z = dc.to_json_slice(7)  # For Plotly heatmap "z" parameter
# z[0][0] might be 0.5432 or None
```

---

## data/model/clumps.py — Clump Catalog

**Location**: `src/jellyscope/data/model/clumps.py`

Manages detected clumps: their physical properties, pixel memberships, and polygon boundaries. The core optimization is the `_clump_map` — a 2D integer array that provides O(1) pixel-to-clump lookup.

### Model: `ClumpProperties`

Pydantic `BaseModel` storing the physical properties of one detected clump. Each field comes directly from a column in `clumps_properties.csv`.

| Field | Type | Description | Example |
| ------- | ------ | ------------- | --------- |
| `clump_id` | `int` | Unique identifier | `4` |
| `area_pix` | `int` | Area in pixels | `144` |
| `area_arcsec2` | `float` | Area in arcsec² | `0.0576` |
| `r_eff_arcsec` | `float` | Effective radius in arcsec | `0.1354` |
| `x0` | `float` | Centroid x (pixel coords) | `115.28` |
| `y0` | `float` | Centroid y (pixel coords) | `159.15` |
| `area_kpc2` | `float` | Area in kpc² | `1.1165` |
| `r_eff_kpc2` | `float` | Effective radius in kpc | `0.5961` |
| `inside` | `bool` | `True` if within galaxy disk | `True` |
| `component` | `str` | `"disk"` or `"outside"` | `"disk"` |

**Astronomy context**:

- `r_eff` (effective radius) = radius containing half the light
- `kpc` (kiloparsec) = ~3,260 light-years
- `arcsec` (arcsecond) = angular unit on the sky

### Class: `ClumpCatalog`

#### `__init__(properties_path, pixels_path, spatial_shape)`

```python
catalog = ClumpCatalog(
    "data/clumps_properties.csv",
    "data/clumps_pixels.csv",
    (221, 172),  # (ny, nx) — from datacube.spatial_shape
)
```

**What happens internally**:

1. Reads `clumps_properties.csv` with pandas → creates `ClumpProperties` for each row → stored in `self.clumps: dict[int, ClumpProperties]`
2. Reads `clumps_pixels.csv` with pandas
3. For each clump, builds a boolean mask `(ny, nx)` from its pixel coordinates
4. Fills `self._clump_map[y, x] = clump_id` for fast lookups

**Internal data structures**:

| Attribute | Type | Description |
| ----------- | ------ | ------------- |
| `clumps` | `dict[int, ClumpProperties]` | Clump ID → properties |
| `_pixels_masks` | `dict[int, np.ndarray]` | Clump ID → boolean mask `(ny, nx)` |
| `_clump_map` | `np.ndarray (int32)` | Shape `(ny, nx)`, each cell = clump_id or `-1` |
| `_boundaries` | `dict[int, list[tuple]]` | Cached boundary polygons (computed lazily) |

#### `get_clump_by_id(clump_id: int) -> ClumpProperties`

Returns the properties for a single clump.

```python
c = catalog.get_clump_by_id(4)
print(c.component)   # "disk"
print(c.area_kpc2)   # 1.1165
```

#### `get_pixel_mask(clump_id: int) -> np.ndarray`

Returns a boolean 2D array of shape `(ny, nx)` where `True` marks pixels belonging to the clump.

```python
mask = catalog.get_pixel_mask(4)
print(mask.sum())  # 144 (number of pixels in clump 4)
```

#### `get_combined_mask(clump_ids: list[int]) -> np.ndarray`

OR-combines masks of multiple clumps into one.

```python
mask = catalog.get_combined_mask([0, 3, 4])
# mask is True wherever any of the 3 clumps have pixels
```

#### `get_clump_id_at_pixel(x: int, y: int) -> int | None`

O(1) lookup. Returns the `clump_id` at pixel `(x, y)`, or `None` if the pixel doesn't belong to any clump.

```python
catalog.get_clump_id_at_pixel(72, 20)   # → 0  (clump 0 is here)
catalog.get_clump_id_at_pixel(0, 0)     # → None (no clump)
```

**How it works**: Simply reads `self._clump_map[y, x]`. Also checks bounds first.

#### `get_boundary_coords(clump_id: int) -> list[tuple[float, float]]`

Returns ordered `(x, y)` coordinates forming a closed polygon around the clump. Uses `scipy.spatial.ConvexHull` for clean outlines.

```python
boundary = catalog.get_boundary_coords(4)
# [(x0, y0), (x1, y1), ..., (x0, y0)]  — last point = first (closed)
```

**Caching**: Boundaries are computed once and cached in `self._boundaries`. Subsequent calls return the cached result.

**Edge cases**:

- Clumps with < 3 pixels: returns a simple polygon of the pixel coordinates
- `QhullError` (collinear points): falls back to listing all pixel coordinates

#### `get_all_boundaries() -> dict[int, list[tuple[float, float]]]`

Returns boundaries for all clumps at once (calls `get_boundary_coords` for each).

#### `list_clumps() -> list[ClumpProperties]`

Returns all clumps as a list.

#### `filter_clumps(component=None, inside=None) -> list[ClumpProperties]`

Filter clumps by component and/or inside status.

```python
disk_clumps = catalog.filter_clumps(component="disk")
outside_clumps = catalog.filter_clumps(component="outside")
inside_clumps = catalog.filter_clumps(inside=True)
```

#### `to_properties_list() -> list[dict]`

Returns all clump properties as a list of JSON-serializable dicts.

---

## data/data_store.py — Dataset and DataStore

**Location**: `src/jellyscope/data/data_store.py`

The data store has two pieces: `Dataset` (a frozen dataclass holding the FITS datacubes and clump catalog for one galaxy) and `DataStore` (a singleton that manages multiple datasets and is shared across HTTP requests).

### Dataclass: `Dataset`

Holds everything loaded from one dataset directory.

| Attribute | Type | Description |
| ----------- | ------ | ------------- |
| `name` | `str` | Dataset identifier (subdirectory name, or `"default"` for the flat layout) |
| `datacubes` | `dict[str, DataCube]` | Datacubes keyed by name (e.g., `"nircam"`, `"nircam_matched"`) |
| `clumps` | `ClumpCatalog \| None` | Clump catalog scoped to this dataset |

#### `get_datacube(name: str) -> DataCube`

Returns the named datacube. Raises `KeyError` listing available names if missing.

#### `list_datacubes() -> list[str]`

Returns names of loaded datacubes for this dataset.

### Class: `DataStore`

Singleton that discovers and holds all `Dataset` instances under `config.data_dir`.

#### `__init__(config: JellyscopeConfig)`

Discovers datasets and loads each one's FITS + CSV files into memory.

```python
store = DataStore(JellyscopeConfig())
```

**Discovery algorithm**:

1. **Subdirectory layout** — every immediate subdirectory of `config.data_dir` containing the expected FITS + clump CSVs is loaded as a `Dataset` named after the directory. Subdirectories are processed in alphabetical order; the first one becomes `default_dataset`.
2. **Flat layout (backward compat)** — when no subdirectories qualify but `config.data_dir` itself contains the expected files at the top level, those are loaded as a single dataset named `"default"`.
3. **Empty / missing** — raises `FileNotFoundError` if `config.data_dir` does not exist or no valid datasets are found.

For each dataset, `_try_load_dataset` requires both clump CSVs plus at least one of the two datacube files. The datacube `nircam` (else `nircam_matched`) provides the `spatial_shape` reference passed to `ClumpCatalog`. Missing optional datacube files are silently skipped.

**Attributes after init**:

| Attribute | Type | Description |
| ----------- | ------ | ------------- |
| `config` | `JellyscopeConfig` | The config used to load |
| `datasets` | `dict[str, Dataset]` | Dataset name → `Dataset` |
| `default_dataset` | `str` | Name of the default dataset (first alphabetical, or `"default"` for flat layout) |

#### `list_datasets() -> list[str]`

Returns names of all loaded datasets.

```python
store.list_datasets()  # ["galaxy_a", "galaxy_b"]  or  ["default"]
```

#### `get_dataset(name: str) -> Dataset`

Returns the named `Dataset`. Raises `KeyError` listing available names if missing.

#### `get_datacube(dataset_name: str, datacube_name: str) -> DataCube`

Scoped accessor — returns a single datacube within a dataset.

```python
dc = store.get_datacube("default", "nircam")
dc_m = store.get_datacube("default", "nircam_matched")
```

#### `list_datacubes(dataset_name: str) -> list[str]`

Returns datacube names for one dataset.

#### `get_clumps(dataset_name: str) -> ClumpCatalog`

Returns the clump catalog scoped to one dataset. Raises `KeyError` if the dataset has no catalog loaded.

#### `get(config=None) -> DataStore` (classmethod)

Singleton accessor. Creates the instance on first call, returns it on subsequent calls.

```python
# In FastAPI routes:
store = DataStore.get()  # Always returns the same instance
```

#### `reset() -> None` (classmethod)

Clears the singleton. Used in tests to force re-initialization with different config.

```python
DataStore.reset()  # Next get() will create a fresh instance
```

---

## model/schemas.py — API contract

**Location**: `src/jellyscope/model/schemas.py`

15 Pydantic models defining the request and response shapes for the REST API. Imported by `web/routes.py` to type request bodies and serialize responses.

**Request models**:

| Model | Used by | Purpose |
| ------- | --------- | --------- |
| `RectSelection` | `RegionRequest` | Rectangular region with `x0`, `y0`, `x1`, `y1` (pixel coords) |
| `RegionRequest` | `POST /region/spectrum/...` | Either an explicit pixel list or a `RectSelection` |
| `CompareRequest` | `POST /compare/spectrum/...` | List of `clump_ids` to overlay on one SED figure |

**Response models**:

| Model | Endpoint | Purpose |
| ------- | ---------- | --------- |
| `FilterInfo` | — | One filter's `index`, `name`, `wavelength` (used inside `FiltersResponse`) |
| `ClumpListItem` | — | Compact clump summary for list views (used inside `ClumpsListResponse`) |
| `DatasetsResponse` | `GET /api/datasets` | `{datasets: [...], default: "..."}` |
| `DatacubesResponse` | `GET /datasets/.../datacubes` | List of available datacube names |
| `FiltersResponse` | `GET /datasets/.../filters/{datacube}` | List of `FilterInfo` per channel |
| `ViewerResponse` | `GET /datasets/.../viewer/{datacube}/{ch}` | Plotly figure dict + `filter_name` |
| `RGBViewerResponse` | `GET /datasets/.../viewer/{datacube}/rgb` | Plotly figure dict + `r_filter`, `g_filter`, `b_filter` names |
| `ClumpsListResponse` | `GET /datasets/.../clumps` | List of `ClumpListItem` |
| `ClumpDetailResponse` | `GET /datasets/.../clumps/{id}` | `properties` dict + `boundary` polygon |
| `PixelClumpResponse` | `GET /datasets/.../pixel/{x}/{y}/clump` | `clump_id` (int or `None`) |
| `SpectrumResponse` | Pixel/clump/region SED endpoints | `spectrum` dict + Plotly `figure` |
| `CompareResponse` | `POST /datasets/.../compare/spectrum/...` | Plotly `figure` + per-clump `spectra` list |

---

## spec_analysis/ — Spectral extraction

**Location**: `src/jellyscope/spec_analysis/`

Helper functions that convert a `DataCube` + selection (pixel, clump, or arbitrary mask) into a wavelength-vs-flux dict. Called from `web/routes.py` to serve the SED-gated spectrum endpoints.

### `spectral.py`

#### `extract_pixel_spectrum(datacube: DataCube, x: int, y: int) -> dict`

Returns the SED at one pixel.

```python
spec = extract_pixel_spectrum(dc, 80, 100)
# {"wavelengths": [...], "fluxes": [...], "filter_names": [...]}
```

#### `extract_clump_spectrum(datacube: DataCube, clumps: ClumpCatalog, clump_id: int) -> dict`

Returns the mean SED across all pixels in a clump (also includes per-channel `std`).

#### `extract_region_spectrum(datacube: DataCube, mask: np.ndarray) -> dict`

Returns the mean SED across all `True` pixels in a boolean mask. Used for `POST /region/spectrum/...`.

### `stats.py`

Module exists but is currently unused by the rest of the codebase. Reserved for future statistical helpers.
