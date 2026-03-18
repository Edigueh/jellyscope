# Architecture

This document describes the overall architecture of Jellyscope, how data flows through the system, and the key technical decisions behind the design.

## Layer Diagram

Jellyscope follows a layered architecture where each layer only depends on layers below it:

```plaintext
┌─────────────────────────────────────────────────┐
│                    Browser                      │
│  Plotly.js renders figures, user clicks/selects │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (JSON)
┌──────────────────────▼──────────────────────────┐
│              Web Layer (Flask)                  │
│  routes.py — 10 REST endpoints                  │
│  templates/index.html — SPA page                │
│  static/app.js — frontend controller            │
└──────────┬──────────────────┬───────────────────┘
           │                  │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Visualization      │ │  Analysis             │
│  image_viewer.py    │ │  spectral.py          │
│  spectrum_plot.py   │ │  statistics.py        │
│  properties_panel.py│ │                       │
└──────────┬──────────┘ └──────┬────────────────┘
           │                   │
┌──────────▼───────────────────▼──────────────────┐
│                Data Layer                       │
│  cache.py    — DataStore singleton              │
│  fits_handler.py — DataCube (FITS I/O)          │
│  clumps.py   — ClumpCatalog (CSV + masks)       │
│  config.py   — JellyscopeConfig                 │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Data Files                         │
│  *.fits (datacubes)   *.csv (clump catalogs)    │
└─────────────────────────────────────────────────┘
```

## Data Flow: From FITS to Browser

This is the complete path that data travels from a FITS file on disk to a pixel rendered in the user's browser:

```plaintext
1. FITS file on disk
   │  cut_datacube_nircam.fits (20 x 221 x 172, float64)
   │
2. DataCube.__init__()                    [fits_handler.py:17]
   │  astropy.io.fits.open() → reads data array + header + WCS
   │  Parses FILTER1..FILTER20 from header → filter_names list
   │
3. DataStore.__init__()                   [cache.py:19]
   │  Loads both datacubes + ClumpCatalog into memory (~12MB total)
   │  Singleton: loaded once at app startup, shared across requests
   │
4. Flask request arrives
   │  GET /api/viewer/nircam/7?selected=0,3
   │
5. routes.get_viewer_figure()             [routes.py:60]
   │  Parses URL params → calls build_viewer_figure()
   │
6. build_viewer_figure()                  [image_viewer.py:94]
   │  a) DataCube.get_slice(7) → 2D numpy array (221 x 172)
   │  b) _asinh_stretch() → normalize + arcsinh to handle dynamic range
   │  c) create_galaxy_heatmap() → Plotly heatmap trace dict
   │  d) create_clump_boundary_traces() → 23 scatter traces (polygons)
   │  e) create_centroid_markers() → scatter trace with clump labels
   │  f) Assembles {data: [...], layout: {...}} Plotly figure dict
   │
7. Flask jsonify()
   │  Python dict → JSON string → HTTP response
   │
8. Browser fetch() in app.js              [app.js:63]
   │  Receives JSON → Plotly.react(viewer, fig.data, fig.layout)
   │
9. Plotly.js renders
   │  Heatmap + boundary polygons + centroid markers → interactive SVG/WebGL
```

## User Interaction Flows

### Flow 1: Click on a Clump

When the user clicks on the galaxy image and hits a pixel that belongs to a clump:

```plaintext
Browser                          Server
───────                          ──────
plotly_click event
 → extract (x, y) from point
 │
 ├── GET /api/pixel/{x}/{y}/clump ─────→ ClumpCatalog.get_clump_at_pixel(x, y)
 │                                        Uses _clump_map[y, x] → O(1) lookup
 ←── { "clump_id": 4 } ───────────────┘
 │
 ├── GET /api/clumps/4 ───────────────→ format_clump_properties(clump)
 │                                      get_boundary_coords(4)
 ←── { properties: {...}, boundary: [...] }
 │
 ├── GET /api/clumps/4/spectrum/nircam → extract_clump_spectrum()
 │                                       DataCube.get_mean_spectrum_for_mask(mask)
 ←── { spectrum: {...}, figure: {...} }
 │
 └── Updates UI:
     1. Properties panel → HTML table
     2. Spectrum plot → Plotly SED chart
     3. Viewer → re-renders with clump highlighted (red border)
```

### Flow 2: Change Filter (Slider)

```plaintext
Browser                          Server
───────                          ──────
slider input event
 → state.channel = newValue
 → update filter label text
 │
 └── GET /api/viewer/nircam/{ch} ─────→ build_viewer_figure(datacube, ch, clumps)
     ?selected=0,3                       Same pipeline: slice → stretch → heatmap
 ←── { figure: {...} } ──────────────┘
 │
 └── Plotly.react() → updates heatmap, keeps boundaries intact
```

### Flow 3: Lasso/Rectangle Selection

```plaintext
Browser                          Server
───────                          ──────
User sets mode to "Lasso" or "Rect"
 → Plotly.relayout(viewer, {dragmode: "lasso"})

User draws selection on image
 → plotly_selected event
 → extract pixel coords from selected points
 │
 └── POST /api/region/spectrum/nircam ──→ Build boolean mask from pixel list
     body: { pixels: [[x1,y1], ...] }     extract_region_spectrum(datacube, mask)
                                           nanmean over masked pixels per channel
 ←── { spectrum: {...}, figure: {...} } ┘
 │
 └── Updates spectrum plot with region SED
```

### Flow 4: Multi-Clump Comparison

```plaintext
Browser                          Server
───────                          ──────
User clicks clump 0, then clump 3, then clump 4
 → state.selectedClumps = Set(0, 3, 4)
 │
 └── POST /api/compare/spectrum/nircam ──→ For each clump_id:
     body: { clump_ids: [0, 3, 4] }        extract_clump_spectrum()
                                           create_multi_sed_figure(spectra, labels)
 ←── { figure: {...}, spectra: [...] } ──┘
 │
 └── Spectrum plot shows 3 overlaid SED curves with different colors
```

## Key Technical Decisions

### 1. Arcsinh Stretch for Image Display

**Problem**: Astronomical images have extreme dynamic range. Raw pixel values span several orders of magnitude, so a linear colormap shows only the brightest features.

**Solution**: Apply `arcsinh(x * 10) / arcsinh(10)` after normalizing to the [1st, 99.5th] percentile range. This is the standard astronomical stretch used by SDSS, STScI, and most optical/IR survey viewers.

**Location**: [image_viewer.py:9-21](../src/jellyscope/visualization/image_viewer.py)

```python
def _asinh_stretch(data):
    vmin = np.percentile(finite, 1)
    vmax = np.percentile(finite, 99.5)
    normalized = (clipped - vmin) / (vmax - vmin + 1e-10)
    return np.arcsinh(normalized * 10) / np.arcsinh(10)
```

### 2. O(1) Pixel-to-Clump Lookup with `_clump_map`

**Problem**: When a user clicks on a pixel, we need to instantly determine which clump (if any) it belongs to. Iterating through all 938 pixel entries per click would be slow and inelegant.

**Solution**: Pre-build a 2D integer array `_clump_map` of shape `(ny, nx)` where each cell stores a `clump_id` or `-1`. This gives constant-time pixel-to-clump lookup.

**Location**: [clumps.py:60](../src/jellyscope/data/clumps.py)

```python
self._clump_map = np.full((self.ny, self.nx), -1, dtype=np.int32)
# ... fill during initialization ...

def get_clump_at_pixel(self, x, y):
    val = self._clump_map[y, x]
    return int(val) if val >= 0 else None
```

**Memory cost**: 221 x 172 x 4 bytes = ~148 KB (trivial).

### 3. NaN Handling: `NaN → None` in JSON

**Problem**: FITS astronomical data commonly has `NaN` values (masked regions, detector gaps). JSON doesn't have a `NaN` type, and Plotly.js needs `null` to render transparent gaps.

**Solution**: Replace `NaN` with Python `None` when serializing data. Use `np.nanmean`/`np.nanstd` for all statistical computations so NaN pixels don't corrupt results.

**Locations**:

- [fits_handler.py:78-84](../src/jellyscope/data/fits_handler.py) — `to_json_slice()`
- [image_viewer.py:31-33](../src/jellyscope/visualization/image_viewer.py) — heatmap z values
- [spectral.py:24](../src/jellyscope/analysis/spectral.py) — spectrum fluxes

### 4. DataStore Singleton Pattern

**Problem**: Loading datacubes from FITS files takes ~100ms. We don't want to reload on every HTTP request.

**Solution**: The `DataStore` class uses a class-level singleton (`_instance`). It's initialized once during `create_app()` and all requests access the same in-memory data via `DataStore.get()`.

**Location**: [cache.py:46-52](../src/jellyscope/data/cache.py)

```python
@classmethod
def get(cls, config=None):
    if cls._instance is None:
        cls._instance = cls(config)
    return cls._instance
```

**Trade-off**: This loads all data eagerly (~12MB). For future datasets with many galaxies, this can evolve into lazy-loading with LRU eviction per dataset.

### 5. Server-Side Figure Construction

**Problem**: Should Plotly figures be built on the server (Python) or the client (JavaScript)?

**Decision**: Server-side. The Flask API returns complete Plotly figure dicts `{data: [...], layout: {...}}`, and the browser just calls `Plotly.react(element, fig.data, fig.layout)`.

**Rationale**:

- Keeps the JS thin (~250 lines) — no complex data manipulation in the browser
- Python has astropy/numpy for efficient array operations
- The figure dict format is identical whether built in Python or JS
- Enables server-side caching of frequently-requested figures in the future

### 6. ConvexHull for Clump Boundaries

**Problem**: Each clump is defined by a set of pixels. We need clean polygon outlines for rendering as Plotly scatter traces.

**Decision**: Use `scipy.spatial.ConvexHull` to compute the convex hull of each clump's pixel coordinates, then render the hull vertices as a closed polygon.

**Location**: [clumps.py:94-123](../src/jellyscope/data/clumps.py)

**Trade-off**: Convex hulls don't capture concave clump shapes. For small clumps (5-144 pixels in current data), this is visually acceptable. For more complex shapes, this could be replaced with alpha-shapes or contour tracing.

## Module Dependency Graph

```plaintext
config.py (no dependencies — pure dataclass)
    ↑
fits_handler.py (imports: astropy, numpy)
    ↑
clumps.py (imports: pandas, numpy, scipy)
    ↑
cache.py (imports: config, fits_handler, clumps)
    ↑
    ├── spectral.py (imports: config, fits_handler, clumps)
    ├── statistics.py (imports: fits_handler, clumps)
    │       ↑
    ├── image_viewer.py (imports: fits_handler, clumps)
    ├── spectrum_plot.py (no internal imports)
    ├── properties_panel.py (imports: clumps)
    │       ↑
    └── routes.py (imports: cache, spectral, statistics, image_viewer,
                           spectrum_plot, properties_panel)
            ↑
        web/__init__.py (imports: config, cache, routes)
            ↑
        cli.py (imports: config, web)
```

The key insight is that `config.py` and the data layer have zero upward dependencies, making them usable as standalone libraries without the web layer.
