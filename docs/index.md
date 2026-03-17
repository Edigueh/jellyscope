# Jellyscope Documentation

Jellyscope is an interactive web application for visualizing JWST (James Webb Space Telescope) datacubes of jellyfish galaxies. It allows researchers to explore multi-filter NIRCam images, select regions of galaxies (clumps, tails, disk), and visualize their spectral energy distributions (SEDs) and physical properties.

## Technology Stack

| Layer | Technology | Purpose |
| ------- | ----------- | --------- |
| Data I/O | [astropy](https://www.astropy.org/) | Read FITS datacubes, parse WCS coordinates |
| Numerical | [NumPy](https://numpy.org/), [SciPy](https://scipy.org/) | Array operations, convex hull computation |
| Tabular data | [Pandas](https://pandas.pydata.org/) | Load CSV clump catalogs |
| Web framework | [Flask](https://flask.palletsprojects.com/) | REST API, template rendering |
| Visualization | [Plotly.js](https://plotly.com/javascript/) | Interactive heatmaps, scatter plots, SED charts |
| Package format | [pyproject.toml](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/) | PEP 621 compliant, ready for PyPI |

## Project Structure

```plaintext
jellyscope/
├── pyproject.toml                      # Package definition and dependencies
├── README.md                           # Quick start guide
├── LICENSE                             # MIT license
├── data/                               # Astronomical data (FITS + CSV)
│   ├── cut_datacube_nircam.fits        # NIRCam datacube (20 filters, 221x172 px)
│   ├── cut_datacube_nircam_matched.fits# PSF-matched version
│   ├── clumps_properties.csv           # 23 clumps with physical properties
│   └── clumps_pixels.csv               # 938 pixel-to-clump mappings
│
├── src/jellyscope/                     # Main Python package
│   ├── __init__.py                     # Version: 0.1.0
│   ├── config.py                       # JellyscopeConfig dataclass + filter wavelengths
│   │
│   ├── data/                           # Data loading layer
│   │   ├── fits_handler.py             # DataCube class — FITS I/O, slicing, spectra
│   │   ├── clumps.py                   # ClumpCatalog — properties, masks, boundaries
│   │   └── cache.py                    # DataStore singleton — in-memory data store
│   │
│   ├── analysis/                       # Scientific analysis layer
│   │   ├── spectral.py                 # SED extraction (pixel, clump, region)
│   │   └── statistics.py               # Region statistics (mean, std, min, max)
│   │
│   ├── visualization/                  # Plotly figure builders
│   │   ├── image_viewer.py             # Galaxy heatmap + clump overlays
│   │   ├── spectrum_plot.py            # SED line plots with error bands
│   │   └── properties_panel.py         # Clump property formatting
│   │
│   ├── web/                            # Flask web application
│   │   ├── __init__.py                 # App factory (create_app)
│   │   ├── routes.py                   # 13 REST API endpoints
│   │   ├── templates/index.html        # Single-page HTML template
│   │   └── static/
│   │       ├── app.js                  # Frontend controller (Plotly + fetch)
│   │       └── style.css               # Dark theme CSS
│   │
│   └── cli.py                          # Command-line entry point
│
├── tests/                              # Test suite (31 tests)
│   ├── conftest.py                     # Shared fixtures
│   ├── test_fits_handler.py            # DataCube tests
│   ├── test_clumps.py                  # ClumpCatalog tests
│   ├── test_spectral.py                # Spectral extraction tests
│   └── test_routes.py                  # Flask endpoint tests
│
└── docs/                               # This documentation
```

## Documentation Index

| Document | Description |
| ---------- | ------------- |
| [Architecture](architecture.md) | System layers, data flow, interaction diagrams, technical decisions |
| [Data Layer](data-layer.md) | `config.py`, `fits_handler.py`, `clumps.py`, `cache.py` — all classes and methods |
| [Analysis](analysis.md) | `spectral.py`, `statistics.py` — SED extraction and region statistics |
| [Visualization](visualization.md) | `image_viewer.py`, `spectrum_plot.py`, `properties_panel.py` — Plotly figure builders |
| [API Reference](api-reference.md) | All 13 REST endpoints with parameters, responses, and curl examples |
| [Frontend](frontend.md) | `index.html`, `app.js`, `style.css` — UI layout, JS controller, Plotly events |
| [Extending](extending.md) | How to add new datasets, analysis modules, endpoints, and visualizations |

## Quick Start

```bash
# Install
conda create -n jellyscope python=3.11 -y
conda activate jellyscope
pip install -e .

# Run
jellyscope --data-dir data

# Open http://127.0.0.1:5000

# Test
pip install -e ".[dev]"
pytest
```
