"""Tests for DataStore cache and app factory defaults."""

import pytest

from jellyscope.data.cache import DataStore


def test_unknown_datacube_raises(store):
    with pytest.raises(KeyError, match="Unknown datacube"):
        store.get_datacube("nonexistent")


def test_default_config_fallback():
    DataStore.reset()
    try:
        store = DataStore.get()
        assert store is not None
        assert "nircam" in store.list_datacubes()
    finally:
        DataStore.reset()


def test_create_app_no_config():
    DataStore.reset()
    try:
        from jellyscope.web import create_app

        app = create_app()
        assert app is not None
    finally:
        DataStore.reset()
