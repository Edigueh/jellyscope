# Visualization Layer

The visualization layer builds Plotly figure dictionaries from data. These dicts are sent to the browser as JSON, where `Plotly.react()` renders them. All functions are pure — they take data as input and return Plotly-compatible dicts.

**Files covered**:

- [visualization/image_viewer.py](../src/jellyscope/visualization/image_viewer.py) — Galaxy heatmap + clump overlays
- [visualization/rgb_composite.py](../src/jellyscope/visualization/rgb_composite.py) — RGB composite (percentile+asinh and Lupton)
- [visualization/spectrum_plot.py](../src/jellyscope/visualization/spectrum_plot.py) — SED line plots
- [visualization/properties_panel.py](../src/jellyscope/visualization/properties_panel.py) — Property formatting

---

## visualization/image_viewer.py — Galaxy Viewer

**Location**: `src/jellyscope/visualization/image_viewer.py`

Builds the main galaxy image as a Plotly figure with three types of traces layered together: a heatmap (the image), boundary polygons (clump outlines), and centroid markers (clump labels).

### Stretch Functions

The module provides three intensity stretch functions, selectable via `_normalize_stretch()`. The default is `_log_stretch`.

#### `_log_stretch(data: np.ndarray) -> np.ndarray` (default)

Applies log stretch using astropy's `LogStretch(a=200)` after normalizing to the [10th, 99.98th] percentile range via `AsymmetricPercentileInterval`. This more aggressively boosts faint structure than arcsinh.

**Algorithm**:

1. Mask NaN and non-positive values
2. Compute bounds via `AsymmetricPercentileInterval(10.0, 99.98)`
3. Clip and normalize to [0, 1]
4. Apply `log(200*x + 1) / log(201)`

#### `_asinh_stretch(data: np.ndarray) -> np.ndarray`

Applies arcsinh intensity stretch. Standard in optical/IR astronomy (SDSS, STScI).

**Algorithm**:

1. Clip to [2nd, 99.5th] percentile (removes outlier hot/cold pixels)
2. Normalize to [0, 1]
3. Apply `arcsinh(x * 18) / arcsinh(18)`

The factor of 18 controls the stretch intensity — higher values bring out more faint structure.

#### `_lupton_asinh_stretch(data: np.ndarray, softening=8.0, alpha=None) -> np.ndarray`

Lupton et al. (2004) single-band asinh stretch: `f(x) = arcsinh(alpha*Q*(x-m)) / Q`. Linear for faint features, logarithmic for bright features. Background level `m` and noise `sigma` are estimated via sigma-clipped statistics. If `alpha` is not provided, it is auto-computed from the noise level as `0.02 / sigma`.

**Algorithm**:

1. Estimate background `(m, sigma)` via sigma-clipped stats
2. Compute `alpha = 0.02 / sigma` if not given
3. Apply `arcsinh(alpha * Q * (x - m)) / Q`
4. Normalize to [0, 1] using 99.5th percentile

#### `_power_stretch(data: np.ndarray) -> np.ndarray`

Power stretch using astropy's `PowerStretch(a=0.5)`. Lower exponent = more aggressive on faint features. Uses [20th, 99.5th] percentile bounds.

#### `_normalize_stretch(data, stretch="log") -> np.ndarray`

Dispatcher that applies the given stretch function. Accepts `"log"`, `"lupton_asinh"`, or `"power"`. Defaults to `"log"`.

---

### `create_galaxy_heatmap(slice_data, colorscale="viridis") -> dict`

Creates a single Plotly `heatmap` trace for a 2D image slice. Internally applies `_normalize_stretch()` (log stretch by default).

**Returns** a Plotly trace dict:

```python
{
    "type": "heatmap",
    "z": [[0.12, 0.34, None, ...], ...],  # 2D array, None = transparent
    "colorscale": "viridis",
    "hoverongaps": False,                   # Don't show hover for None pixels
    "hovertemplate": "x: %{x}<br>y: %{y}<br>flux: %{z:.4f}<extra></extra>",
    "showscale": True,
    "colorbar": {"title": "Flux (stretched)", "thickness": 15},
}
```

The `z` array has NaN replaced with `None` so Plotly renders gaps as transparent. The `hoverongaps: False` setting prevents hover tooltips on empty regions.

---

### `create_clump_boundary_traces(clumps, selected_ids=None) -> list[dict]`

Creates one Plotly `scatter` trace per clump, rendering its boundary as a closed polygon.

**Visual styling**:

- **Default clumps**: cyan (`#00ccff`), thin lines (width 1.2)
- **Selected clumps**: red (`#ff4444`), thicker lines (width 2.5)

Each trace contains:

```python
{
    "type": "scatter",
    "x": [x0, x1, ..., x0],       # Boundary x coords (closed polygon)
    "y": [y0, y1, ..., y0],       # Boundary y coords
    "mode": "lines",
    "line": {"color": "#00ccff", "width": 1.2},
    "name": "Clump 4",
    "hoverinfo": "text",
    "text": "Clump 4 (disk)",      # Shown on hover
    "showlegend": False,
}
```

Returns a list of 23 traces (one per clump in the toy data).

---

### `create_centroid_markers(clumps) -> dict`

Creates a single scatter trace with all clump centroids as `x` markers with ID labels.

```python
{
    "type": "scatter",
    "x": [71.8, 77.4, ...],           # Centroid x coords
    "y": [19.9, 96.2, ...],           # Centroid y coords
    "mode": "markers+text",
    "marker": {"color": "#ffffff", "size": 5, "symbol": "x"},
    "text": ["0", "1", ...],          # Clump IDs as labels
    "textposition": "top right",
    "textfont": {"color": "#cccccc", "size": 9},
    "hovertemplate": "Clump %{text}<br>x: %{x:.1f}<br>y: %{y:.1f}<extra></extra>",
    "name": "Centroids",
    "showlegend": False,
}
```

---

### `build_viewer_figure(datacube, channel_index, clumps, selected_ids=None, colorscale="Viridis", stretch="log") -> dict`

**Main entry point**. Assembles the complete Plotly figure by combining all the traces above with a layout.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | Datacube to visualize |
| `channel_index` | `int` | Which filter channel to display |
| `clumps` | `ClumpCatalog` | Clump catalog for overlays |
| `selected_ids` | `list[int] \| None` | Clumps to highlight in red |
| `colorscale` | `str` | Plotly colorscale name |
| `stretch` | `str` | `"log"`, `"lupton_asinh"`, or `"power"` |

**Returns**: Complete Plotly figure dict:

```python
{
    "data": [
        { heatmap trace },
        { boundary trace for clump 0 },
        { boundary trace for clump 1 },
        ...
        { boundary trace for clump 22 },
        { centroid markers trace },
    ],
    "layout": {
        "title": {"text": "cut_datacube_nircam — F200W"},
        "xaxis": {"title": "x (pixels)", "scaleanchor": "y"},
        "yaxis": {"title": "y (pixels)"},
        "plot_bgcolor": "#1a1a2e",      # Dark theme
        "paper_bgcolor": "#16213e",
        "dragmode": "pan",               # Default interaction mode
        "margin": {"l": 50, "r": 20, "t": 40, "b": 50},
    }
}
```

The `scaleanchor: "y"` ensures the aspect ratio is preserved (1 pixel = 1 pixel on screen).

Total traces: 1 (heatmap) + 23 (boundaries) + 1 (centroids) = **25 traces**.

---

## visualization/properties_panel.py — Property Formatting

**Location**: `src/jellyscope/visualization/properties_panel.py`

### `format_clump_properties(clump: ClumpProperties) -> dict`

Converts a `ClumpProperties` model into a human-readable display dict.

**Returns**:

```python
{
    "Clump ID": 4,
    "Component": "Disk",                # Capitalized
    "Inside disk": "Yes",               # Bool → "Yes"/"No"
    "Area (pixels)": 144,
    "Area (arcsec²)": "0.0576",         # Formatted to 4 decimals
    "Area (kpc²)": "1.1165",
    "R_eff (arcsec)": "0.1354",
    "R_eff (kpc)": "0.5961",
    "Centroid x": "115.3",              # Formatted to 1 decimal
    "Centroid y": "159.1",
}
```

This dict is sent to the frontend, where `app.js` renders it as an HTML table:

```html
<table class="prop-table">
    <tr><td>Clump ID</td><td>4</td></tr>
    <tr><td>Component</td><td>Disk</td></tr>
    ...
</table>
```

---

## visualization/rgb_composite.py — RGB Composite

**Location**: `src/jellyscope/visualization/rgb_composite.py`

The module offers two RGB composite methods, selectable at call time:

- **`percentile_asinh`** (default) — per-band median subtract, percentile clip, asinh stretch, pedestal cut. Not strictly color-preserving, but produces clean, deep-field-style images. Recipe contributed by Andressa.
- **`lupton`** — Lupton et al. (2004) Eq. 2 color-preserving mapping. The output color of an object depends only on its flux ratios, not its brightness.

### `RGBMethod` type alias

```python
RGBMethod = Literal["percentile_asinh", "lupton"]
```

Used by `build_rgb_figure` and the corresponding FastAPI endpoint to dispatch between the two methods.

### `percentile_asinh_composite(r_data, g_data, b_data, pmin=10.0, pmax=99.9, scale=0.1, floor=0.05, weights=(1.0, 1.02, 1.02)) -> np.ndarray`

Per-band, independent stretch pipeline.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `r_data`, `g_data`, `b_data` | `np.ndarray` | 2D flux arrays |
| `pmin`, `pmax` | `float` | Percentile bounds for the linear clip (in percent) |
| `scale` | `float` | asinh softening; smaller boosts faint features more |
| `floor` | `float` | Pedestal cut applied after the stretch — pixels below become 0 |
| `weights` | `tuple[float, float, float]` | Per-channel multipliers `(wR, wG, wB)` applied at the end |

**Algorithm** (per band, then combined): median-subtract → percentile-clip to `[pmin, pmax]` → asinh stretch via `arcsinh(y/scale) / arcsinh(1/scale)` → floor cut → channel weight. NaN-safe: any pixel non-finite in any band becomes black.

The actual per-band work is done by the private helper `_normalize_band_asinh`.

### `lupton_rgb_composite(r_data, g_data, b_data, softening=8.0, alpha=None) -> np.ndarray`

Lupton et al. (2004) Eq. 2.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `r_data` | `np.ndarray` | 2D flux array for the red channel |
| `g_data` | `np.ndarray` | 2D flux array for the green channel |
| `b_data` | `np.ndarray` | 2D flux array for the blue channel |
| `softening` | `float` | Q parameter controlling linear-to-log transition (typical: 8-9) |
| `alpha` | `float \| None` | Linear stretch factor. Auto-estimated from noise if None |

**Algorithm**:

1. Compute total intensity: `I = (R + G + B) / 3`
2. Estimate background `(m, sigma)` via sigma-clipped stats
3. Compute `alpha = 0.02 / sigma` if not given
4. Apply asinh stretch to intensity: `f(I) = arcsinh(alpha * Q * (I - m)) / Q`
5. Color-preserving scale: `ratio = f(I) / (I - m)`
6. Scale each band: `R_out = (R - m) * ratio`, etc.
7. Per-pixel saturation clamping: if max(R,G,B) > 1, scale down to preserve hue
8. Global normalization to [0,1] using 99.5th percentile
9. Return uint8 array of shape `(ny, nx, 3)`

### `build_rgb_figure(datacube, r_index, g_index, b_index, clumps, selected_ids=None, method="percentile_asinh", softening=8.0, alpha=None) -> dict`

Assembles the Plotly figure with RGB image + clump overlays.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | Datacube to visualize |
| `r_index`, `g_index`, `b_index` | `int` | Channel indices for the R, G, B bands |
| `clumps` | `ClumpCatalog` | Clump catalog for overlays |
| `selected_ids` | `list[int] \| None` | Clumps to highlight in red |
| `method` | `RGBMethod` | `"percentile_asinh"` (default) or `"lupton"` |
| `softening` | `float` | Lupton Q — only used when `method="lupton"` |
| `alpha` | `float \| None` | Lupton linear stretch factor — only used when `method="lupton"` |

**Coordinate system note**: Plotly's `go.Image` renders array row 0 at the top (y-axis increases downward), while heatmaps render row 0 at the bottom. To match single-band visual orientation:

1. The image is flipped vertically (`np.flipud`)
2. Boundary/centroid y-coordinates are transformed: `y_new = ny - 1 - y`
3. The y-axis uses `autorange: "reversed"` to keep y=0 at the bottom

All three are required for correct alignment between the RGB image and scatter overlays.

---

## visualization/spectrum_plot.py — SED Plots

**Location**: `src/jellyscope/visualization/spectrum_plot.py`

Builds Plotly line charts for Spectral Energy Distributions (SEDs).

### `create_sed_figure(spectrum, title="Spectral Energy Distribution") -> dict`

Creates a single SED plot with flux vs wavelength. If the spectrum dict contains `std_flux`, a filled ±1σ uncertainty band is added.

**Input `spectrum` dict**:

```python
{
    "wavelengths": [0.704, 0.901, ...],   # µm
    "mean_flux": [1.2e-3, 1.5e-3, ...],   # or "fluxes" for single pixel
    "std_flux": [2e-4, 3e-4, ...],         # optional
    "filter_names": ["F070W", "F090W", ...],
}
```

### `create_multi_sed_figure(spectra, labels) -> dict`

Overlays multiple SEDs on one plot for comparison. Each SED gets a distinct color from an 8-color palette. Used by the `/api/compare/spectrum/` endpoint.

---
