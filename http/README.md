# HTTP Requests

Executable `.http` files for every Jellyscope REST endpoint. Open any of them in
an IDE that supports the `.http` format and click "Send Request" next to a
`### Title` block.

## Compatible clients

- [VS Code REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension
- JetBrains HTTP Client (built into IntelliJ IDEA, PyCharm, WebStorm, etc.)

Both honor the `### Title` separator, the `@host = ...` variable syntax, and
inline comments starting with `#`.

## Setup

1. Start the dev server:
   ```sh
   just serve-dev
   ```
   This binds `127.0.0.1:5000` (the default `@host` in `_env.http`).
2. Open any `*.http` file in this directory and click the "Send Request" lens
   above the request you want to run.

## File map

| File | Endpoints |
| --- | --- |
| [`pages.http`](pages.http) | `GET /` |
| [`datasets.http`](datasets.http) | dataset, datacube, and filter discovery |
| [`viewer.http`](viewer.http) | single-band and RGB viewer figures |
| [`clumps.http`](clumps.http) | clump list, pairwise separations, single clump detail |
| [`pixel.http`](pixel.http) | pixel-to-clump lookup |

`_env.http` defines the shared `@host` variable. Every other file imports it via
the `{{host}}` placeholder. To target a deployed instance, edit `_env.http` or
override `@host` at the top of an individual file.

## Example values

The example values come from real defaults:

- `dataset_name`: `default` (from `DEFAULT_DATASET` in `data_store.py`)
- `datacube_name`: `nircam` or `nircam_matched` (from `data_store.py`)
- `channel_index`: `7` → F200W (from `NIRCAM_WAVELENGTHS` in `config.py`)
- RGB defaults: `r=7` (F200W), `g=2` (F115W), `b=1` (F090W) — match
  `DEFAULT_RGB` in `config.py`
- `clump_id`: `4` (a real clump in the bundled dataset)
- pixel coords: `72,20` (sample inside a known clump)

Replace these with values appropriate for your dataset.

## Source of truth

These files are kept in sync with `src/jellyscope/web/routes.py` and
`src/jellyscope/model/schemas.py`. When endpoints change, update the matching
`.http` block.
