# Jellyscope

Interactive web application for visualizing JWST jellyfish galaxy datacubes.

Jellyscope lets you explore multi-filter NIRCam datacubes, select regions of galaxies (clumps, tails, disk), and visualize their spectral energy distributions (SEDs) and physical properties.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
uv sync --extra dev
```

## Usage

```bash
uv run jellyscope --data-dir data
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

## Development

This project uses modern Python tooling managed via [uv](https://docs.astral.sh/uv/) and a [`justfile`](https://just.systems/) (install with `brew install just` on macOS).

```bash
just               # List available recipes
just install       # Install deps + set up pre-commit hooks
just lint          # Run ruff linter
just lint-fix      # Auto-fix lint issues
just format        # Format code with ruff
just typecheck     # Run mypy type checking
just test          # Run tests with coverage
just test-fast     # Quick test run (no coverage, stop on first failure)
just check         # Run ALL checks (lint + format + typecheck + tests)
just spellcheck    # Check for typos in code/docs
just serve         # Start the dev server
just clean         # Remove build artifacts
```

### Tooling

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Package management, venv, lockfile |
| [ruff](https://docs.astral.sh/ruff/) | Linting + formatting |
| [mypy](https://mypy.readthedocs.io/) | Static type checking |
| [pre-commit](https://pre-commit.com/) | Git hooks (lint, format, typecheck before each commit) |
| [codespell](https://github.com/codespell-project/codespell) | Typo detection |

## Project Structure

```
src/jellyscope/
├── config.py           # Configuration
├── data/               # FITS I/O, clump catalog, data store
├── analysis/           # Spectral extraction, statistics
├── visualization/      # Plotly figure builders
├── web/                # FastAPI app, REST API, frontend
└── cli.py              # Command-line entry point
```

## License

MIT
