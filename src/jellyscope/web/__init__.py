"""Flask application factory."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore


def create_app(config: JellyscopeConfig | None = None) -> FastAPI:
    """Create and configure the Flask application."""
    if config is None:
        config = JellyscopeConfig()

    app = FastAPI(title="Jellyscope", version="0.1.0")
    app.state.config = config

    # Pre-load data into memory.
    DataStore.get(config)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    template_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(template_dir))
    templates.env.filters["tojson"] = lambda val: json.dumps(val)
    app.state.templates = templates

    from jellyscope.web.routes import router

    app.include_router(router)

    return app
