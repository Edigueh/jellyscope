"""Shared test fixtures."""

import pytest
from pathlib import Path

from jellyscope.config import JellyscopeConfig
from jellyscope.data.cache import DataStore


@pytest.fixture(scope="session")
def config():
    return JellyscopeConfig(data_dir=Path("data"))


@pytest.fixture(scope="session")
def store(config):
    DataStore.reset()
    return DataStore.get(config)


@pytest.fixture()
def app(config):
    from jellyscope.web import create_app
    DataStore.reset()
    app = create_app(config)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
