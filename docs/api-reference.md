# API Reference

Jellyscope exposes a REST API over HTTP. All data endpoints return JSON. The API is defined in [routes.py](../src/jellyscope/web/routes.py) using FastAPI's `APIRouter`.

**Base URL**: `http://127.0.0.1:5000` (default)

All data endpoints are scoped under `/api/datasets/{dataset_name}/`. Use `GET /api/datasets` to list available datasets and the default.

---

## Pages

### `GET /`

Serves the main single-page application HTML.

```bash
curl http://localhost:5000/
```

Returns the rendered `index.html` template with Jinja2 variables populated (datasets, filters, wavelengths, etc.).

---

## Datasets

### `GET /api/datasets`

List all available datasets and the default dataset name.

```bash
curl http://localhost:5000/api/datasets
```

**Response**:

```json
{
    "datasets": ["galaxy_a", "galaxy_b"],
    "default": "galaxy_a"
}
```

For a flat layout (files directly in `data/`), `datasets` will be `["default"]`.

---

## Datacube Information

### `GET /api/datasets/{dataset_name}/datacubes`

List all available datacubes within a dataset.

```bash
curl http://localhost:5000/api/datasets/default/datacubes
```

**Response**:

```json
{
    "datacubes": ["nircam", "nircam_matched"]
}
```

---

### `GET /api/datasets/{dataset_name}/filters/{datacube_name}`

List all filter channels for a datacube, with their wavelengths.

```bash
curl http://localhost:5000/api/datasets/default/filters/nircam
```

**Path parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `dataset_name` | `string` | Dataset name (from `/api/datasets`) |
| `datacube_name` | `string` | Datacube name (`"nircam"` or `"nircam_matched"`) |

**Response**:

```json
{
    "filters": [
        {"index": 0, "name": "F070W", "wavelength": 0.704},
        {"index": 1, "name": "F090W", "wavelength": 0.901},
        ...
        {"index": 19, "name": "F480M", "wavelength": 4.834}
    ]
}
```

---

## Image Viewer

### `GET /api/datasets/{dataset_name}/viewer/{datacube_name}/{channel_index}`

Returns a complete Plotly figure (heatmap + clump overlays + centroids) ready for `Plotly.react()`.

```bash
# F200W (channel 7), with clumps 0 and 4 selected
curl "http://localhost:5000/api/datasets/default/viewer/nircam/7?selected=0,4&colorscale=Viridis&stretch=log"
```

**Path parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `dataset_name` | `string` | Dataset name |
| `datacube_name` | `string` | Datacube name |
| `channel_index` | `int` | Filter channel index (0-19) |

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `selected` | `string` | `""` | Comma-separated clump IDs to highlight |
| `colorscale` | `string` | `"Viridis"` | Plotly colorscale name |
| `stretch` | `string` | `"log"` | Intensity stretch: `"log"`, `"lupton_asinh"`, or `"power"` |

**Error responses**:

- `400` — channel index out of range
- `422` — invalid stretch value

**Response**:

```json
{
    "figure": {
        "data": [
            {"type": "heatmap", "z": [[...]], ...},
            {"type": "scatter", "x": [...], "y": [...], "name": "Clump 0", ...},
            ...
        ],
        "layout": {
            "title": {"text": "cut_datacube_nircam — F200W"},
            "xaxis": {"title": "x (pixels)"},
            "yaxis": {"title": "y (pixels)"},
            "plot_bgcolor": "#1a1a2e",
            ...
        }
    },
    "filter_name": "F200W"
}
```

---

### `GET /api/datasets/{dataset_name}/viewer/{datacube_name}/rgb`

Returns an RGB composite Plotly figure with clump overlays. Two stretch methods are available, selectable via the `method` query parameter:

- **`percentile_asinh`** (default) — per-band median subtract, percentile clip, asinh stretch, and pedestal cut. Recipe contributed by Andressa; produces clean, deep-field-style images.
- **`lupton`** — Lupton et al. (2004) Eq. 2 color-preserving mapping. Output color depends only on flux ratios, not brightness. The `softening` (Q) parameter applies only to this method.

The RGB image is rendered as a PNG embedded in `layout.images[]` (not as a `go.Image` trace). An invisible `heatmap` trace with `opacity: 0` over the same extent carries click/hover events so `plotly_click` returns coordinates in raw FITS pixel space. Boundary and centroid traces use raw FITS pixel coordinates — **no `ny-1-y` transform** needed at the trace level.

```bash
# Default method (percentile_asinh) with R=F200W (ch 7), G=F115W (ch 2), B=F090W (ch 1)
curl "http://localhost:5000/api/datasets/default/viewer/nircam/rgb?r=7&g=2&b=1&method=percentile_asinh"

# Lupton method with custom softening
curl "http://localhost:5000/api/datasets/default/viewer/nircam/rgb?r=19&g=10&b=0&method=lupton&softening=8.0"
```

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `r` | `int` | required | Red channel filter index |
| `g` | `int` | required | Green channel filter index |
| `b` | `int` | required | Blue channel filter index |
| `selected` | `string` | `""` | Comma-separated clump IDs to highlight |
| `method` | `"percentile_asinh"` \| `"lupton"` | `"percentile_asinh"` | Stretch method |
| `softening` | `float` | `8.0` | Lupton Q parameter (only used when `method="lupton"`) |

**Error responses**:

- `400` — channel index out of range
- `422` — invalid `method` value

**Response**:

```json
{
    "figure": {
        "data": [
            {"type": "heatmap", "z": null, "opacity": 0, ...},
            {"type": "scatter", "name": "Clump 0", ...},
            ...
        ],
        "layout": {
            "images": [{"source": "data:image/png;base64,...", ...}],
            ...
        }
    },
    "r_filter": "F200W",
    "g_filter": "F115W",
    "b_filter": "F090W"
}
```

Note: `data[0]` is the invisible heatmap click target, not the image. The PNG lives in `layout.images[0].source`.

---

## Clumps

### `GET /api/datasets/{dataset_name}/clumps`

List all detected clumps with basic properties.

```bash
# All clumps
curl http://localhost:5000/api/datasets/default/clumps

# Only disk clumps
curl "http://localhost:5000/api/datasets/default/clumps?component=disk"

# Only clumps outside the disk
curl "http://localhost:5000/api/datasets/default/clumps?component=outside&inside=false"
```

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `component` | `string` | all | `"disk"` or `"outside"` |
| `inside` | `bool` | all | `true` or `false` |

**Response**:

```json
{
    "clumps": [
        {
            "clump_id": 0,
            "x0": 71.79,
            "y0": 19.93,
            "area_pix": 121,
            "component": "outside",
            "inside": false
        },
        ...
    ]
}
```

---

### `GET /api/datasets/{dataset_name}/clumps/{clump_id}`

Get detailed properties and boundary polygon for a single clump.

```bash
curl http://localhost:5000/api/datasets/default/clumps/4
```

**Response**:

```json
{
    "properties": {
        "Clump ID": 4,
        "Component": "Disk",
        "Inside disk": "Yes",
        "Area (pixels)": 144,
        "Area (arcsec²)": "0.0576",
        "Area (kpc²)": "1.1165",
        "R_eff (arcsec)": "0.1354",
        "R_eff (kpc)": "0.5961",
        "Centroid x": "115.3",
        "Centroid y": "159.1"
    },
    "boundary": [
        [108.0, 148.0],
        [124.0, 149.0],
        ...
        [108.0, 148.0]
    ]
}
```

---

## Pixel Interaction

### `GET /api/datasets/{dataset_name}/pixel/{x}/{y}/clump`

Identify which clump (if any) a pixel belongs to. O(1) lookup.

```bash
curl http://localhost:5000/api/datasets/default/pixel/72/20/clump
```

**Response** (pixel belongs to clump 0):

```json
{"clump_id": 0}
```

**Response** (pixel has no clump):

```json
{"clump_id": null}
```

---

## JavaScript `fetch()` Examples

These examples show how the frontend calls the API (from [app.js](../src/jellyscope/web/static/app.js)). `DATASET` is the active dataset name (injected from the template as `DEFAULT_DATASET`):

```javascript
// Get viewer figure (single-band)
const resp = await fetch(`/api/datasets/${DATASET}/viewer/nircam/7?selected=0,4&colorscale=Viridis&stretch=log`);
const data = await resp.json();
Plotly.react("galaxy-viewer", data.figure.data, data.figure.layout);

// Get RGB composite (default percentile_asinh method)
const resp = await fetch(`/api/datasets/${DATASET}/viewer/nircam/rgb?r=7&g=2&b=1&method=percentile_asinh`);
const data = await resp.json();
Plotly.react("galaxy-viewer", data.figure.data, data.figure.layout);

// Check clump at pixel
const resp = await fetch(`/api/datasets/${DATASET}/pixel/72/20/clump`);
const { clump_id } = await resp.json();

// Get clump details
const resp = await fetch(`/api/datasets/${DATASET}/clumps/4`);
const { properties, boundary } = await resp.json();
```
