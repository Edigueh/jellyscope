"""Shared test fixtures."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore

SESSION_SCOPE: str = "session"


@pytest.fixture(scope=SESSION_SCOPE)
def config() -> JellyscopeConfig:
    return JellyscopeConfig(data_dir=Path("data"), enable_sed=True)


@pytest.fixture(scope=SESSION_SCOPE)
def store(config: JellyscopeConfig) -> "DataStore":
    DataStore.reset()
    return DataStore.get(config)


@pytest.fixture
def app(config: JellyscopeConfig) -> FastAPI:
    from jellyscope.web import create_app

    DataStore.reset()
    return create_app(config)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
