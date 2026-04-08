"""Tests for Flask routes."""

from flask import Flask


def test_routes(app: Flask):
    assert app.config["TESTING"]
