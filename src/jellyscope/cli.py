"""Command-line entry point for Jellyscope."""

import argparse
from pathlib import Path

import uvicorn

from jellyscope.config import JellyscopeConfig
from jellyscope.web import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Jellyscope: JWST Jellyfish Galaxy Explorer")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument(
        "--data-dir", default="data", help="Path to data directory (default: data)"
    )
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
    args = parser.parse_args()

    config = JellyscopeConfig(
        data_dir=Path(args.data_dir),
        host=args.host,
        port=args.port,
        debug=not args.no_debug,
    )
    app = create_app(config)
    print(f"Starting Jellyscope on http://{config.host}:{config.port}")
    print(f"Data directory: {config.data_dir.resolve()}")
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()
