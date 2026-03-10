"""Command-line entry point for Jellyscope."""

import argparse
from pathlib import Path

from .config import JellyscopeConfig
from .web import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jellyscope: JWST Jellyfish Galaxy Explorer"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--data-dir", default="data", help="Path to data directory (default: data)")
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
    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    main()
