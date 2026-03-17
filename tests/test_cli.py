"""Tests for CLI entry point."""

from unittest.mock import patch

from jellyscope.cli import main


def test_main_default_args():
    with (
        patch("sys.argv", ["jellyscope", "--data-dir", "data"]),
        patch("jellyscope.cli.create_app") as mock_create_app,
    ):
        mock_app = mock_create_app.return_value
        mock_app.run = lambda **kwargs: None
        main()
        mock_create_app.assert_called_once()
        config = mock_create_app.call_args[0][0]
        assert config.host == "127.0.0.1"
        assert config.port == 5000
        assert config.debug is True


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
                "--no-debug",
                "--data-dir",
                "data",
            ],
        ),
        patch("jellyscope.cli.create_app") as mock_create_app,
    ):
        mock_app = mock_create_app.return_value
        mock_app.run = lambda **kwargs: None
        main()
        config = mock_create_app.call_args[0][0]
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.debug is False
