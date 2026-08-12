"""Resolve Vite-built frontend assets for the index template.

Two modes:

- **Built** (default): read ``static/dist/.vite/manifest.json`` once and expose
  the hashed entry JS + CSS under relative ``static/dist/...`` URLs (relative so
  they survive the HF Space HTTPS proxy — see the mixed-content gotcha).
- **Dev**: when ``JELLYSCOPE_VITE_DEV`` is set (e.g. ``http://localhost:5173``),
  point at the Vite dev server for HMR instead of built files.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_ENTRY = "src/main.tsx"


@dataclass(frozen=True)
class ViteAssets:
    """Asset URLs + dev flag the index template needs."""

    dev_server: str | None
    js: str = ""
    css: list[str] = field(default_factory=list)

    @property
    def is_dev(self) -> bool:
        return self.dev_server is not None


def load_vite_assets(static_dir: Path) -> ViteAssets:
    """Resolve entry assets. Prefers dev server, else the built manifest."""
    dev = os.environ.get("JELLYSCOPE_VITE_DEV")
    if dev:
        return ViteAssets(dev_server=dev.rstrip("/"))

    manifest_path = static_dir / "dist" / ".vite" / "manifest.json"
    if not manifest_path.is_file():
        # No build yet — template renders the bare mount; useful before first build.
        return ViteAssets(dev_server=None)

    manifest = json.loads(manifest_path.read_text())
    entry = manifest.get(_ENTRY, {})
    js = entry.get("file", "")
    css = list(entry.get("css", []))
    return ViteAssets(
        dev_server=None,
        js=f"static/dist/{js}" if js else "",
        css=[f"static/dist/{c}" for c in css],
    )
