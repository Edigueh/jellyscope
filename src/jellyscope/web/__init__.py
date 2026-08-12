"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jellyscope._bootstrap import ensure_data
from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore
from jellyscope.web.vite import load_vite_assets


def create_app(config: JellyscopeConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = JellyscopeConfig()

    app = FastAPI(title="Jellyscope", version="0.1.0")
    app.state.config = config

    # Compress large figure JSON — the app is bandwidth-bound behind the HF
    # proxy (fine locally over loopback). Halves the multi-MB viewer payloads.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # Pre-load data into memory.
    ensure_data(config.data_dir)
    DataStore.get(config)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Resolve built (or dev-server) frontend assets once at startup.
    app.state.vite = load_vite_assets(static_dir)

    template_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(template_dir))
    app.state.templates = templates

    from jellyscope.web.routes import router

    app.include_router(router)

    return app
