"""Flask application factory."""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def create_app(config: JellyscopeConfig | None = None) -> FastAPI:
    """Create and configure the Flask application."""
    if config is None:
        config = JellyscopeConfig()

    # Env-driven feature flags override config defaults.
    config = config.model_copy(
        update={"enable_sed": _env_bool("JELLYSCOPE_ENABLE_SED", config.enable_sed)}
    )

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
