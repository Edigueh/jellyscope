"""Tests for CLI entry point."""

from unittest.mock import patch

from jellyscope.cli import main


def test_main_default_args():
    with (
        patch("sys.argv", ["jellyscope", "--data-dir", "data"]),
        patch("jellyscope.cli.create_app") as mock_create_app,
        patch("jellyscope.cli.uvicorn") as mock_uvicorn,
    ):
        main()
        mock_create_app.assert_called_once()
        config = mock_create_app.call_args[0][0]
        assert config.host == "127.0.0.1"
        assert config.port == 5000
        mock_uvicorn.run.assert_called_once()


def test_main_custom_args():
    with (
        patch(
            "sys.argv",
            [
                "jellyscope",
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--data-dir",
                "data",
            ],
        ),
        patch("jellyscope.cli.create_app") as mock_create_app,
        patch("jellyscope.cli.uvicorn") as mock_uvicorn,
    ):
        main()
        config = mock_create_app.call_args[0][0]
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        mock_uvicorn.run.assert_called_once()
