# Extending Jellyscope

This guide explains how to add new data, features, and modules to Jellyscope.

---

## 1. Adding a New Dataset

A dataset is a collection of FITS datacubes and CSV clump catalogs for one galaxy observation.

### Step 1: Prepare the data files

Place your files in the `data/` directory (or a subdirectory):

```plaintext
data/
├── my_new_galaxy.fits              # 3D FITS: (n_filters, ny, nx), float64
├── my_new_galaxy_matched.fits      # Optional: PSF-matched version
├── clumps_properties.csv           # Clump properties (same column names)
└── clumps_pixels.csv               # Clump pixel coordinates
```

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

Create a new file in `src/jellyscope/analysis/`:

```python
# src/jellyscope/analysis/color_magnitude.py
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

In `routes.py`, add:

```python
@router.get("/api/cmd/{datacube_name}")
def get_color_magnitude(datacube_name: str):
    store = _store()
    dc = store.get_datacube(datacube_name)

    from jellyscope.analysis.color_magnitude import compute_clump_colors
    from jellyscope.visualization.color_magnitude_plot import create_cmd_figure

    blue = "F150W"
    red = "F444W"
    data = compute_clump_colors(dc, store.clumps, blue, red)
    figure = create_cmd_figure(data)
    return {"data": data, "figure": figure}
```

### Step 4: Add to the frontend (optional)

In `index.html`, add a new panel or button. In `app.js`, add a fetch call:

```javascript
async function showCMD() {
    const resp = await fetch(`/api/cmd/${state.datacube}?blue=F150W&red=F444W`);
    const data = await resp.json();
    Plotly.react("cmd-plot", data.figure.data, data.figure.layout);
}
```

---

## 3. Adding a New REST Endpoint

All endpoints are in [routes.py](../src/jellyscope/web/routes.py). Follow this pattern:

```python
@router.get("/api/your-endpoint/{datacube_name}")
def your_endpoint(datacube_name: str):
    store = _store()                          # Get the DataStore singleton
    dc = store.get_datacube(datacube_name)    # Get the datacube
    # ... compute something ...
    return {"result": ...}                    # Return dict (auto-serialized to JSON)
```

**Conventions**:

- Prefix all API routes with `/api/`
- Use path parameters for required IDs: `/api/clumps/{clump_id}`
- Use query parameters for optional filters: `?component=disk`
- POST for requests with complex bodies (pixel lists, clump ID arrays)
- Return dicts or Pydantic response models (FastAPI handles JSON serialization)

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

## 6. Supporting Multiple Galaxies

To evolve Jellyscope to handle multiple galaxies, you could organize data as subdirectories:

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

Then extend `DataStore` to lazily load datasets:

```python
class DataStore:
    def __init__(self, config):
        self._datasets: dict[str, dict] = {}
        # Scan data_dir for subdirectories
        for subdir in config.data_dir.iterdir():
            if subdir.is_dir() and (subdir / "datacube.fits").exists():
                self._datasets[subdir.name] = {"path": subdir, "loaded": False}

    def get_dataset(self, name: str):
        ds = self._datasets[name]
        if not ds["loaded"]:
            ds["datacube"] = DataCube(ds["path"] / "datacube.fits")
            ds["clumps"] = ClumpCatalog(...)
            ds["loaded"] = True
        return ds
```

This keeps memory usage proportional to the number of actively viewed galaxies, not the total collection.
