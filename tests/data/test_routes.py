"""Tests for Flask routes."""

from fastapi import FastAPI


def test_routes(app: FastAPI):
    assert app.title == "Jellyscope"
