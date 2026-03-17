# API Reference

Jellyscope exposes a REST API over HTTP. All data endpoints return JSON. The API is defined in [routes.py](../src/jellyscope/web/routes.py).

**Base URL**: `http://127.0.0.1:5000` (default)

---

## Pages

### `GET /`

Serves the main single-page application HTML.

```bash
curl http://localhost:5000/
```

Returns the rendered `index.html` template with Jinja2 variables populated (datacube list, filter names).

---

## Datacube Information

### `GET /api/datacubes`

List all available datacubes.

```bash
curl http://localhost:5000/api/datacubes
```

**Response**:

```json
{
    "datacubes": ["nircam", "nircam_matched"]
}
```

---

### `GET /api/filters/<datacube_name>`

List all filter channels for a datacube, with their wavelengths.

```bash
curl http://localhost:5000/api/filters/nircam
```

**Path parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
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

### `GET /api/viewer/<datacube_name>/<channel_index>`

Returns a complete Plotly figure (heatmap + clump overlays + centroids) ready for `Plotly.react()`.

```bash
# F200W (channel 7), with clumps 0 and 4 selected
curl "http://localhost:5000/api/viewer/nircam/7?selected=0,4&colorscale=Viridis"
```

**Path parameters**:

| Param | Type | Description |
| ------- | ------ | ------------- |
| `datacube_name` | `string` | Datacube name |
| `channel_index` | `int` | Filter channel index (0-19) |

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `selected` | `string` | `""` | Comma-separated clump IDs to highlight |
| `colorscale` | `string` | `"Viridis"` | Plotly colorscale name |

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

## Clumps

### `GET /api/clumps`

List all detected clumps with basic properties.

```bash
# All clumps
curl http://localhost:5000/api/clumps

# Only disk clumps
curl "http://localhost:5000/api/clumps?component=disk"

# Only clumps outside the disk
curl "http://localhost:5000/api/clumps?component=outside&inside=false"
```

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `component` | `string` | all | `"disk"` or `"outside"` |
| `inside` | `string` | all | `"true"` or `"false"` |

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

### `GET /api/clumps/<clump_id>`

Get detailed properties and boundary polygon for a single clump.

```bash
curl http://localhost:5000/api/clumps/4
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

### `GET /api/clumps/<clump_id>/spectrum/<datacube_name>`

Extract the mean SED for a clump, plus a pre-built Plotly figure.

```bash
curl http://localhost:5000/api/clumps/4/spectrum/nircam
```

**Response**:

```json
{
    "spectrum": {
        "filter_names": ["F070W", "F090W", ...],
        "wavelengths": [0.704, 0.901, ...],
        "mean_flux": [0.0234, 0.0567, ...],
        "std_flux": [0.0012, 0.0034, ...],
        "n_pixels": 144,
        "clump_id": 4
    },
    "figure": {
        "data": [...],
        "layout": {...}
    }
}
```

---

## Pixel Interaction

### `GET /api/pixel/<x>/<y>/clump`

Identify which clump (if any) a pixel belongs to. O(1) lookup.

```bash
curl http://localhost:5000/api/pixel/72/20/clump
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

### `GET /api/pixel/<x>/<y>/spectrum/<datacube_name>`

Extract the SED at a single pixel.

```bash
curl http://localhost:5000/api/pixel/80/100/spectrum/nircam
```

**Response**:

```json
{
    "spectrum": {
        "filter_names": ["F070W", ...],
        "wavelengths": [0.704, ...],
        "fluxes": [0.0123, 0.0456, ...],
        "n_pixels": 1
    },
    "figure": {
        "data": [...],
        "layout": {...}
    }
}
```

---

## Region Selection

### `POST /api/region/spectrum/<datacube_name>`

Extract the mean SED from an arbitrary region defined by pixel coordinates or a rectangle.

**Option A: Pixel list** (from lasso selection):

```bash
curl -X POST http://localhost:5000/api/region/spectrum/nircam \
  -H "Content-Type: application/json" \
  -d '{"pixels": [[72, 20], [73, 20], [74, 21], [73, 21]]}'
```

**Option B: Rectangle**:

```bash
curl -X POST http://localhost:5000/api/region/spectrum/nircam \
  -H "Content-Type: application/json" \
  -d '{"rect": {"x0": 70, "y0": 15, "x1": 80, "y1": 25}}'
```

**Request body**:

| Field | Type | Description |
| ------- | ------ | ------------- |
| `pixels` | `list[list[int]]` | List of `[x, y]` pairs |
| `rect` | `object` | Rectangle with `x0, y0, x1, y1` |

Only one of `pixels` or `rect` should be provided. If both are present, `pixels` takes precedence.

**Response**:

```json
{
    "spectrum": {
        "filter_names": ["F070W", ...],
        "wavelengths": [0.704, ...],
        "mean_flux": [0.034, ...],
        "std_flux": [0.012, ...],
        "n_pixels": 4
    },
    "figure": {
        "data": [...],
        "layout": {...}
    }
}
```

---

## Multi-Clump Comparison

### `POST /api/compare/spectrum/<datacube_name>`

Compare SEDs of multiple clumps overlaid on one plot.

```bash
curl -X POST http://localhost:5000/api/compare/spectrum/nircam \
  -H "Content-Type: application/json" \
  -d '{"clump_ids": [0, 3, 4]}'
```

**Request body**:

| Field | Type | Description |
| ------- | ------ | ------------- |
| `clump_ids` | `list[int]` | List of clump IDs to compare |

**Response**:

```json
{
    "figure": {
        "data": [
            {"type": "scatter", "name": "Clump 0 (outside)", ...},
            {"type": "scatter", "name": "Clump 3 (disk)", ...},
            {"type": "scatter", "name": "Clump 4 (disk)", ...}
        ],
        "layout": {...}
    },
    "spectra": [
        {"filter_names": [...], "mean_flux": [...], "clump_id": 0, ...},
        {"filter_names": [...], "mean_flux": [...], "clump_id": 3, ...},
        {"filter_names": [...], "mean_flux": [...], "clump_id": 4, ...}
    ]
}
```

---

## JavaScript `fetch()` Examples

These examples show how the frontend calls the API (from [app.js](../src/jellyscope/web/static/app.js)):

```javascript
// Get viewer figure
const resp = await fetch(`/api/viewer/nircam/7?selected=0,4&colorscale=Viridis`);
const data = await resp.json();
Plotly.react("galaxy-viewer", data.figure.data, data.figure.layout);

// Check clump at pixel
const resp = await fetch(`/api/pixel/72/20/clump`);
const { clump_id } = await resp.json();

// Region spectrum (lasso selection)
const resp = await fetch(`/api/region/spectrum/nircam`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pixels: [[72, 20], [73, 21]] }),
});

// Multi-clump comparison
const resp = await fetch(`/api/compare/spectrum/nircam`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clump_ids: [0, 3, 4] }),
});
```
