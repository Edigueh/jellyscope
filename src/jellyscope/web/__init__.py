"""Flask application factory."""

from fastapi import FastAPI

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

    from .routes import router

    app.include_router(router)

    return app
