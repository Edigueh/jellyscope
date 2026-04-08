"""Shared test fixtures."""

from pathlib import Path

import pytest
from flask import Flask

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore

SESSION_SCOPE: str = "session"


@pytest.fixture(scope=SESSION_SCOPE)
def config() -> JellyscopeConfig:
    return JellyscopeConfig(data_dir=Path("data"))


@pytest.fixture(scope=SESSION_SCOPE)
def store(config: JellyscopeConfig) -> "DataStore":
    DataStore.reset()
    return DataStore.get(config)


@pytest.fixture
def app(config: JellyscopeConfig) -> Flask:
    from jellyscope.web import create_app

    DataStore.reset()
    app: Flask = create_app(config)
    app.config["TESTING"] = True
    return app
