# Visualization Layer

The visualization layer builds Plotly figure dictionaries from data. These dicts are sent to the browser as JSON, where `Plotly.react()` renders them. All functions are pure — they take data as input and return Plotly-compatible dicts.

**Files covered**:

- [visualization/image_viewer.py](../src/jellyscope/visualization/image_viewer.py) — Galaxy heatmap + clump overlays
- [visualization/spectrum_plot.py](../src/jellyscope/visualization/spectrum_plot.py) — SED line plots
- [visualization/properties_panel.py](../src/jellyscope/visualization/properties_panel.py) — Property formatting

---

## visualization/image_viewer.py — Galaxy Viewer

**Location**: `src/jellyscope/visualization/image_viewer.py`

Builds the main galaxy image as a Plotly figure with three types of traces layered together: a heatmap (the image), boundary polygons (clump outlines), and centroid markers (clump labels).

### `_asinh_stretch(data: np.ndarray) -> np.ndarray`

**Private**. Applies arcsinh intensity stretch to a 2D image array.

**Why arcsinh?** Astronomical images have extreme dynamic range — the galaxy core might be 1000x brighter than the faint tails. A linear colormap would render the tails as invisible black. The `arcsinh` function behaves like `log(x)` for large values but is defined at zero (unlike `log`), making it the standard choice in optical/IR astronomy.

**Algorithm**:

1. Clip to [1st, 99.5th] percentile (removes outlier hot/cold pixels)
2. Normalize to [0, 1]
3. Apply `arcsinh(x * 10) / arcsinh(10)`

The factor of 10 controls the stretch intensity — higher values bring out more faint structure.

```python
raw_slice = datacube.get_slice(7)         # Linear values
stretched = _asinh_stretch(raw_slice)     # Values in [0, 1], faint features visible
```

---

### `create_galaxy_heatmap(slice_data, filter_name, colorscale="Viridis") -> dict`

Creates a single Plotly `heatmap` trace for a 2D image slice.

**Returns** a Plotly trace dict:

```python
{
    "type": "heatmap",
    "z": [[0.12, 0.34, None, ...], ...],  # 2D array, None = transparent
    "colorscale": "Viridis",
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

### `build_viewer_figure(datacube, channel_index, clumps, selected_ids=None, colorscale="Viridis") -> dict`

**Main entry point**. Assembles the complete Plotly figure by combining all the traces above with a layout.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube` | `DataCube` | Datacube to visualize |
| `channel_index` | `int` | Which filter channel to display |
| `clumps` | `ClumpCatalog` | Clump catalog for overlays |
| `selected_ids` | `list[int] \| None` | Clumps to highlight in red |
| `colorscale` | `str` | Plotly colorscale name |

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

## visualization/spectrum_plot.py — SED Plots

**Location**: `src/jellyscope/visualization/spectrum_plot.py`

### `create_sed_figure(spectrum, title="Spectral Energy Distribution") -> dict`

Creates a Plotly figure showing flux vs. wavelength (the SED).

**Input `spectrum` dict** must have:

- `wavelengths`: list of wavelengths in microns
- `mean_flux` or `fluxes`: list of flux values
- Optionally `std_flux`: list of standard deviations
- Optionally `filter_names`: list of filter names for hover text

**Main trace**: `scatter` with `lines+markers` mode, cyan color (`#00ccff`).

**Error band** (if `std_flux` provided): A filled area trace showing +/- 1 standard deviation, rendered as a semi-transparent cyan band (`rgba(0, 204, 255, 0.15)`). This is created using the `fill: "toself"` technique where upper and lower bounds are concatenated into a single closed polygon.

**Hover template**: Shows filter name, wavelength, and flux value:

```plaintext
F200W
λ: 1.990 μm
Flux: 3.4567e-01
```

---

### `create_multi_sed_figure(spectra, labels) -> dict`

Overlays multiple SEDs for comparison, each in a different color.

**Parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `spectra` | `list[dict]` | List of spectrum dicts |
| `labels` | `list[str]` | Display name for each spectrum |

**Color palette**: Cycles through 8 colors:

1. `#00ccff` (cyan)
2. `#ff4444` (red)
3. `#44ff44` (green)
4. `#ffaa00` (orange)
5. `#ff44ff` (magenta)
6. `#44ffff` (light cyan)
7. `#ffff44` (yellow)
8. `#aa44ff` (purple)

The legend is shown (unlike single SED plots) so users can identify which curve belongs to which clump.

---

## visualization/properties_panel.py — Property Formatting

**Location**: `src/jellyscope/visualization/properties_panel.py`

### `format_clump_properties(clump: ClumpProperties) -> dict`

Converts a `ClumpProperties` dataclass into a human-readable display dict.

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
