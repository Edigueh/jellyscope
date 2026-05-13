# API Reference

Jellyscope exposes a REST API over HTTP. All data endpoints return JSON. The API is defined in [routes.py](../src/jellyscope/web/routes.py) using FastAPI's `APIRouter`.

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

### `GET /api/filters/{datacube_name}`

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

### `GET /api/viewer/{datacube_name}/{channel_index}`

Returns a complete Plotly figure (heatmap + clump overlays + centroids) ready for `Plotly.react()`.

```bash
# F200W (channel 7), with clumps 0 and 4 selected
curl "http://localhost:5000/api/viewer/nircam/7?selected=0,4&colorscale=Viridis&stretch=log"
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

### `GET /api/viewer/{datacube_name}/rgb`

Returns an RGB composite Plotly figure using the Lupton et al. (2004) algorithm.

```bash
curl "http://localhost:5000/api/viewer/nircam/rgb?r=19&g=10&b=0&softening=8.0"
```

**Query parameters**:

| Param | Type | Default | Description |
| ------- | ------ | --------- | ------------- |
| `r` | `int` | required | Red channel filter index |
| `g` | `int` | required | Green channel filter index |
| `b` | `int` | required | Blue channel filter index |
| `selected` | `string` | `""` | Comma-separated clump IDs to highlight |
| `softening` | `float` | `8.0` | Q parameter (controls linear-to-log transition) |

**Error responses**:

- `400` — channel index out of range

**Response**:

```json
{
    "figure": {
        "data": [
            {"type": "image", "z": [[[r,g,b], ...]], ...},
            {"type": "scatter", ...},
            ...
        ],
        "layout": {...}
    },
    "r_filter": "F480M",
    "g_filter": "F277W",
    "b_filter": "F070W"
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

### `GET /api/clumps/{clump_id}`

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

## Pixel Interaction

### `GET /api/pixel/{x}/{y}/clump`

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

## JavaScript `fetch()` Examples

These examples show how the frontend calls the API (from [app.js](../src/jellyscope/web/static/app.js)):

```javascript
// Get viewer figure (single-band)
const resp = await fetch(`/api/viewer/nircam/7?selected=0,4&colorscale=Viridis&stretch=log`);
const data = await resp.json();
Plotly.react("galaxy-viewer", data.figure.data, data.figure.layout);

// Get RGB composite
const resp = await fetch(`/api/viewer/nircam/rgb?r=19&g=10&b=0&softening=8.0`);
const data = await resp.json();
Plotly.react("galaxy-viewer", data.figure.data, data.figure.layout);

// Check clump at pixel
const resp = await fetch(`/api/pixel/72/20/clump`);
const { clump_id } = await resp.json();

// Get clump details
const resp = await fetch(`/api/clumps/4`);
const { properties, boundary } = await resp.json();
```

---

## Spectral Extraction

### `GET /api/clumps/{clump_id}/spectrum/{datacube_name}`

Mean SED for a clump (flux averaged over all pixels in the clump mask).

```bash
curl http://localhost:5000/api/clumps/0/spectrum/nircam
```

**Response**:

```json
{
    "spectrum": {
        "filter_names": ["F070W", "F090W", ...],
        "wavelengths": [0.704, 0.901, ...],
        "mean_flux": [1.2e-3, 1.5e-3, ...],
        "std_flux": [2e-4, 3e-4, ...],
        "n_pixels": 121,
        "clump_id": 0
    },
    "figure": { "data": [...], "layout": {...} }
}
```

---

### `GET /api/pixel/{x}/{y}/spectrum/{datacube_name}`

SED for a single pixel.

```bash
curl http://localhost:5000/api/pixel/80/100/spectrum/nircam
```

**Response**:

```json
{
    "spectrum": {
        "filter_names": ["F070W", ...],
        "wavelengths": [0.704, ...],
        "fluxes": [3.1e-4, ...],
        "n_pixels": 1
    },
    "figure": { "data": [...], "layout": {...} }
}
```

---

### `POST /api/region/spectrum/{datacube_name}`

Mean SED for an arbitrary region (rectangle or pixel list).

```bash
curl -X POST http://localhost:5000/api/region/spectrum/nircam \
  -H "Content-Type: application/json" \
  -d '{"rect": {"x0": 70, "y0": 15, "x1": 80, "y1": 25}}'
```

**Request body** (one of):

```json
{"rect": {"x0": 70, "y0": 15, "x1": 80, "y1": 25}}
```

or:

```json
{"pixels": [[72, 20], [73, 20], [74, 21]]}
```

**Response**: Same shape as clump spectrum (with `mean_flux`, `std_flux`, `n_pixels`).

---

### `POST /api/compare/spectrum/{datacube_name}`

Overlay multiple clump SEDs for comparison.

```bash
curl -X POST http://localhost:5000/api/compare/spectrum/nircam \
  -H "Content-Type: application/json" \
  -d '{"clump_ids": [0, 1, 3]}'
```

**Response**:

```json
{
    "spectra": [
        {"filter_names": [...], "wavelengths": [...], "mean_flux": [...], ...},
        ...
    ],
    "figure": { "data": [...], "layout": {...} }
}
```
