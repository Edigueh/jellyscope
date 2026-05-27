# Extending Jellyscope

This guide explains how to add new data, features, and modules to Jellyscope.

---

## 1. Adding a New Dataset

A dataset is a collection of FITS datacubes and CSV clump catalogs for one galaxy observation. Each dataset is a subdirectory of `data/` (the directory name becomes the dataset's API identifier). A flat `data/` (files directly under it) is loaded as a single dataset called `default`.

### Step 1: Prepare the data files

Place your files in a subdirectory of `data/`:

```plaintext
data/
└── my_new_galaxy/                      # Becomes dataset name "my_new_galaxy"
    ├── datacube.fits                   # 3D FITS: (n_filters, ny, nx), float64
    ├── datacube_matched.fits           # Optional: PSF-matched version
    ├── clumps_properties.csv           # Clump properties (same column names)
    └── clumps_pixels.csv               # Clump pixel coordinates
```

`DataStore` discovers all subdirectories at startup; the first (alphabetical) becomes the `default_dataset`. Add more subdirectories to expose more datasets — no code changes required.

**FITS requirements**:

- Primary HDU with 3D data array `(n_channels, ny, nx)`
- Header keys `FILTER1`, `FILTER2`, ..., `FILTERn` with filter names
- Standard WCS keys (`CTYPE1`, `CTYPE2`, `CRVAL1`, etc.) are optional but recommended

**CSV requirements**:

- `clumps_properties.csv` columns: `clump_id, area_pix, area_arcsec2, r_eff_arcsec, x0, y0, area_kpc2, r_eff_kpc, inside, component`
- `clumps_pixels.csv` columns: `clump_id, x, y`
- Pixel coordinates must be within the datacube spatial dimensions

### Step 2: Update configuration

Edit `config.py` or pass a custom config:

```python
config = JellyscopeConfig(
    data_dir=Path("data"),
    datacube_file="my_new_galaxy.fits",
    datacube_matched_file="my_new_galaxy_matched.fits",
)
```

Or run from CLI:

```bash
jellyscope --data-dir data
```

### Step 3: Add filter wavelengths (if different instrument)

If your datacube uses filters not in `NIRCAM_WAVELENGTHS`, update the config:

```python
config = JellyscopeConfig(
    filter_wavelengths={
        "F560W": 5.6,
        "F770W": 7.7,
        # ... MIRI filters for example
    }
)
```

Or add them to `NIRCAM_WAVELENGTHS` in `config.py`.

---

## 2. Adding a New Analysis Module

### Step 1: Create the module

Create a new file in `src/jellyscope/spec_analysis/`:

```python
# src/jellyscope/spec_analysis/color_magnitude.py
"""Color-magnitude diagram analysis."""

import numpy as np
from ..data.model.datacube import DataCube
from ..data.model.clumps import ClumpCatalog


def compute_clump_colors(
    datacube: DataCube,
    clumps: ClumpCatalog,
    blue_filter: str,
    red_filter: str,
) -> list[dict]:
    """Compute color (blue - red) and magnitude for each clump."""
    results = []
    for c in clumps.list_clumps():
        mask = clumps.get_pixel_mask(c.clump_id)
        blue = datacube.get_slice_by_name(blue_filter)[mask]
        red = datacube.get_slice_by_name(red_filter)[mask]
        color = -2.5 * np.log10(np.nanmean(blue) / np.nanmean(red))
        mag = -2.5 * np.log10(np.nanmean(red))
        results.append({
            "clump_id": c.clump_id,
            "color": float(color),
            "magnitude": float(mag),
            "component": c.component,
        })
    return results
```

### Step 2: Add a visualization (optional)

```python
# src/jellyscope/visualization/color_magnitude_plot.py

def create_cmd_figure(data: list[dict]) -> dict:
    """Create a color-magnitude diagram Plotly figure."""
    disk = [d for d in data if d["component"] == "disk"]
    outside = [d for d in data if d["component"] == "outside"]

    return {
        "data": [
            {
                "type": "scatter",
                "x": [d["color"] for d in disk],
                "y": [d["magnitude"] for d in disk],
                "mode": "markers",
                "name": "Disk",
                "marker": {"color": "#44ff44"},
            },
            {
                "type": "scatter",
                "x": [d["color"] for d in outside],
                "y": [d["magnitude"] for d in outside],
                "mode": "markers",
                "name": "Outside",
                "marker": {"color": "#ffaa00"},
            },
        ],
        "layout": {
            "title": {"text": "Color-Magnitude Diagram"},
            "xaxis": {"title": "Color (mag)"},
            "yaxis": {"title": "Magnitude", "autorange": "reversed"},
            "plot_bgcolor": "#1a1a2e",
            "paper_bgcolor": "#16213e",
            "font": {"color": "#cccccc"},
        },
    }
```

### Step 3: Add a REST endpoint

In `routes.py`, add (note the `/api/datasets/{dataset_name}/` namespace and the `_dataset(name)` helper):

```python
@router.get("/api/datasets/{dataset_name}/cmd/{datacube_name}")
def get_color_magnitude(dataset_name: str, datacube_name: str):
    dataset = _dataset(dataset_name)          # Resolve dataset by name (404 if missing)
    dc = dataset.get_datacube(datacube_name)  # Get the datacube on that dataset

    from jellyscope.spec_analysis.color_magnitude import compute_clump_colors
    from jellyscope.visualization.color_magnitude_plot import create_cmd_figure

    blue = "F150W"
    red = "F444W"
    data = compute_clump_colors(dc, dataset.clumps, blue, red)
    figure = create_cmd_figure(data)
    return {"data": data, "figure": figure}
```

If the response shape is non-trivial, define a Pydantic model in `src/jellyscope/model/schemas.py` and return it instead of a bare dict — that file is the single source of truth for the API contract.

### Step 4: Add to the frontend (optional)

In `index.html`, add a new panel or button. In `app.js`, add a fetch call:

```javascript
async function showCMD() {
    const resp = await fetch(`/api/datasets/${state.dataset}/cmd/${state.datacube}?blue=F150W&red=F444W`);
    const data = await resp.json();
    Plotly.react("cmd-plot", data.figure.data, data.figure.layout);
}
```

---

## 3. Adding a New REST Endpoint

All endpoints are in [routes.py](../src/jellyscope/web/routes.py). Every data endpoint is namespaced under `/api/datasets/{dataset_name}/...` so the dataset is explicit in the URL. Follow this pattern:

```python
@router.get("/api/datasets/{dataset_name}/your-endpoint/{datacube_name}")
def your_endpoint(dataset_name: str, datacube_name: str):
    dataset = _dataset(dataset_name)          # Helper: resolves dataset or 404s
    dc = dataset.get_datacube(datacube_name)  # Get the datacube
    # ... compute something ...
    return {"result": ...}                    # Return dict or Pydantic model
```

For SED-like routes that should be opt-in, add `_require_sed_enabled(request)` at the top of the handler — it 404s when `JellyscopeConfig.enable_sed = False`.

**Conventions**:

- Prefix all data routes with `/api/datasets/{dataset_name}/`
- Use path parameters for required IDs: `/api/datasets/{dataset_name}/clumps/{clump_id}`
- Use query parameters for optional filters: `?component=disk`
- POST for requests with complex bodies (pixel lists, clump ID arrays)
- Define request/response Pydantic models in `src/jellyscope/model/schemas.py` and reference them via `response_model=...` (FastAPI handles JSON serialization)

---

## 4. Adding a New Visualization

Visualization modules in `src/jellyscope/visualization/` are pure functions that return Plotly figure dicts. They follow this pattern:

```python
def create_my_figure(data: ...) -> dict:
    """Create a Plotly figure for X."""
    return {
        "data": [
            {"type": "scatter", "x": [...], "y": [...], ...},
        ],
        "layout": {
            "title": {"text": "My Plot", "font": {"color": "#cccccc"}},
            "xaxis": {"title": "X Label", "gridcolor": "#333", "color": "#999"},
            "yaxis": {"title": "Y Label", "gridcolor": "#333", "color": "#999"},
            "plot_bgcolor": "#1a1a2e",
            "paper_bgcolor": "#16213e",
            "font": {"color": "#cccccc"},
            "margin": {"l": 60, "r": 20, "t": 40, "b": 50},
        },
    }
```

**Dark theme values** (copy these for consistency):

- `plot_bgcolor`: `#1a1a2e`
- `paper_bgcolor`: `#16213e`
- `font.color`: `#cccccc`
- `gridcolor`: `#333`
- `axis.color`: `#999`

---

## 5. Publishing as a PyPI Package

The project is already structured for this. Steps:

### Build

```bash
pip install build
python -m build
# Creates dist/jellyscope-0.1.0.tar.gz and dist/jellyscope-0.1.0-py3-none-any.whl
```

### Test locally

```bash
pip install dist/jellyscope-0.1.0-py3-none-any.whl
jellyscope --data-dir /path/to/data
```

### Publish to PyPI

```bash
pip install twine
twine upload dist/*
```

### Publish to TestPyPI (for testing)

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ jellyscope
```

### Version bump

Update the version in two places:

1. `pyproject.toml`: `version = "0.2.0"`
2. `src/jellyscope/__init__.py`: `__version__ = "0.2.0"`

---

## 6. Multiple Galaxies (already supported)

`DataStore` already discovers multiple galaxies as subdirectories of `config.data_dir`. Drop your data in:

```plaintext
data/
├── jw2736-jfg1/
│   ├── datacube.fits
│   ├── datacube_matched.fits
│   ├── clumps_properties.csv
│   └── clumps_pixels.csv
├── jw2736-jfg2/
│   └── ...
```

Each subdirectory is loaded as a `Dataset` named after the directory. The first (alphabetical) becomes `default_dataset`. A flat layout (files directly under `data/`) is loaded as a single dataset called `default` for backward compatibility.

The frontend exposes the active dataset via `DEFAULT_DATASET` (template-injected) and `state.dataset` (JS), so all `/api/datasets/${state.dataset}/...` calls automatically scope to it. To let the user switch galaxies, add a `<select>` populated from `DATASETS` and update `state.dataset` on change before re-rendering.

---

## 7. Enabling SED Endpoints

The four spectrum endpoints (`clumps/{id}/spectrum`, `pixel/{x}/{y}/spectrum`, `region/spectrum`, `compare/spectrum`) are gated by `JellyscopeConfig.enable_sed` and return 404 by default. To enable them:

```python
config = JellyscopeConfig(
    data_dir=Path("data"),
    enable_sed=True,
)
```

The CLI does not yet expose a `--enable-sed` flag — set it on the config object in code, or wire one up in `cli.py` as a small extension.
