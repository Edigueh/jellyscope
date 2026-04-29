# Jellyscope Documentation

Jellyscope is an interactive web application for visualizing JWST (James Webb Space Telescope) datacubes of jellyfish galaxies. It allows researchers to explore multi-filter NIRCam images, select regions of galaxies (clumps, tails, disk), and visualize their spectral energy distributions (SEDs) and physical properties.

## Technology Stack

| Layer | Technology | Purpose |
| ------- | ----------- | --------- |
| Data I/O | [astropy](https://www.astropy.org/) | Read FITS datacubes, parse WCS coordinates |
| Numerical | [NumPy](https://numpy.org/), [SciPy](https://scipy.org/) | Array operations, convex hull computation |
| Tabular data | [Pandas](https://pandas.pydata.org/) | Load CSV clump catalogs |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) | REST API, template rendering, ASGI server |
| Visualization | [Plotly.js](https://plotly.com/javascript/) | Interactive heatmaps, scatter plots, SED charts |
| Validation | [Pydantic](https://docs.pydantic.dev/) | Configuration and response models |
| Package format | [pyproject.toml](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/) | PEP 621 compliant, ready for PyPI |

## Project Structure

```plaintext
jellyscope/
├── pyproject.toml                      # Package definition and dependencies
├── README.md                           # Quick start guide
├── LICENSE                             # MIT license
├── Makefile                            # Development commands
├── data/                               # Astronomical data (FITS + CSV)
│   ├── cut_datacube_nircam.fits        # NIRCam datacube (20 filters, 221x172 px)
│   ├── cut_datacube_nircam_matched.fits# PSF-matched version
│   ├── clumps_properties.csv           # 23 clumps with physical properties
│   └── clumps_pixels.csv              # 938 pixel-to-clump mappings
│
├── src/jellyscope/                     # Main Python package
│   ├── __init__.py                     # Version: 0.1.0
│   ├── config.py                       # JellyscopeConfig (Pydantic) + filter wavelengths
│   ├── cli.py                          # Command-line entry point
│   │
│   ├── data/                           # Data loading layer
│   │   ├── __init__.py
│   │   ├── data_store.py              # DataStore singleton — in-memory data store
│   │   └── model/
│   │       ├── datacube.py            # DataCube class — FITS I/O, slicing, spectra
│   │       └── clumps.py             # ClumpCatalog — properties, masks, boundaries
│   │
│   ├── model/                          # Response models
│   │   └── schemas.py                 # Pydantic schemas for API responses
│   │
│   ├── visualization/                  # Plotly figure builders
│   │   ├── __init__.py
│   │   ├── image_viewer.py            # Galaxy heatmap + clump overlays
│   │   └── properties_panel.py        # Clump property formatting
│   │
│   └── web/                            # FastAPI web application
│       ├── __init__.py                 # App factory (create_app)
│       ├── routes.py                   # 7 REST API endpoints
│       ├── templates/index.html        # Single-page HTML template
│       └── static/
│           ├── app.js                  # Frontend controller (Plotly + fetch)
│           └── style.css              # Dark theme CSS
│
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── conftest.py                     # Shared fixtures
│   ├── test_cli.py                     # CLI entry point tests
│   ├── data/
│   │   ├── test_datacube.py           # DataCube tests
│   │   └── test_clumps.py            # ClumpCatalog tests
│   └── web/
│       └── test_routes.py             # API endpoint tests
│
└── docs/                               # This documentation
```

## Documentation Index

| Document | Description |
| ---------- | ------------- |
| [Architecture](architecture.md) | System layers, data flow, interaction diagrams, technical decisions |
| [Data Layer](data-layer.md) | `config.py`, `data_store.py`, `model/datacube.py`, `model/clumps.py` — all classes and methods |
| [Visualization](visualization.md) | `image_viewer.py`, `properties_panel.py` — Plotly figure builders |
| [API Reference](api-reference.md) | All 7 REST endpoints with parameters, responses, and curl examples |
| [Frontend](frontend.md) | `index.html`, `app.js`, `style.css` — UI layout, JS controller, Plotly events |
| [Extending](extending.md) | How to add new datasets, analysis modules, endpoints, and visualizations |

## Quick Start

```bash
# Install
uv sync --extra dev

# Run
uv run jellyscope --data-dir data

# Open http://127.0.0.1:5000

# Test
uv run pytest
```
