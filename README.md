# Jellyscope

Interactive web application for visualizing JWST jellyfish galaxy datacubes.

Jellyscope lets you explore multi-filter NIRCam datacubes, select regions of galaxies (clumps, tails, disk), and visualize their spectral energy distributions (SEDs) and physical properties.

## Features

- **Interactive galaxy viewer** — Plotly heatmap with arcsinh stretch, pan/zoom, and clump boundary overlays
- **Clump selection** — Click on detected clumps to view properties and SEDs
- **Region selection** — Draw rectangles or lasso regions to extract spectra from arbitrary areas
- **Multi-clump comparison** — Select multiple clumps to overlay their SEDs
- **Filter navigation** — Slider to browse all 20 NIRCam filters (0.7–4.8 μm)
- **Dual datacubes** — Switch between original and PSF-matched datacubes

## Installation

```bash
conda create -n jellyscope python=3.11 -y
conda activate jellyscope
pip install -e .
```

## Usage

```bash
jellyscope --data-dir data
```

Then open http://127.0.0.1:5000 in your browser.

### Options

```
--host HOST       Server host (default: 127.0.0.1)
--port PORT       Server port (default: 5000)
--data-dir DIR    Path to data directory (default: data)
--no-debug        Disable debug mode
```

## Data Format

Place your data in the `data/` directory:

- **FITS datacubes** — 3D arrays with shape `(n_filters, ny, nx)` and `FILTER1..FILTERn` header keys
- **clumps_properties.csv** — Columns: `clump_id, area_pix, area_arcsec2, r_eff_arcsec, x0, y0, area_kpc2, r_eff_kpc, inside, component`
- **clumps_pixels.csv** — Columns: `clump_id, x, y`

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## Project Structure

```
src/jellyscope/
├── config.py           # Configuration
├── data/               # FITS I/O, clump catalog, data store
├── analysis/           # Spectral extraction, statistics
├── visualization/      # Plotly figure builders
├── web/                # Flask app, REST API, frontend
└── cli.py              # Command-line entry point
```

## License

MIT
