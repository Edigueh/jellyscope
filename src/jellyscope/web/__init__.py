"""Flask application factory."""

from flask import Flask

from ..config import JellyscopeConfig
from ..data.cache import DataStore


def create_app(config: JellyscopeConfig | None = None) -> Flask:
    """Create and configure the Flask application."""
    if config is None:
        config = JellyscopeConfig()

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.config["JELLYSCOPE"] = config

    # Pre-load data into memory
    DataStore.get(config)

    from .routes import bp
    app.register_blueprint(bp)

    return app
