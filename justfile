mod docker
mod check

[doc('List recipes')]
default:
    @just --list

[doc('Install all dependencies including dev + pre-commit hooks')]
install:
    uv sync --extra dev
    uv run pre-commit install
    cd frontend && npm ci

[doc('Install frontend deps only')]
ui-install:
    cd frontend && npm ci

[doc('Build the frontend bundle into the served static dir')]
ui-build:
    cd frontend && npm run build

[doc('Vite dev server (HMR) — pair with `just serve-dev-hmr`')]
ui-dev:
    cd frontend && npm run dev

[doc('Build frontend, then start the production-style server')]
serve: ui-build
    uv run jellyscope --data-dir data

[doc('Start with auto-reload; serves the last-built frontend bundle')]
serve-dev:
    uv run uvicorn jellyscope.web:create_app --factory --reload --host 127.0.0.1 --port 5000

[doc('Backend with reload, wired to the Vite dev server for HMR (run `just ui-dev` alongside)')]
serve-dev-hmr:
    JELLYSCOPE_VITE_DEV=http://localhost:5173 uv run uvicorn jellyscope.web:create_app --factory --reload --host 127.0.0.1 --port 5000

[doc('Clean build artifacts')]
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info
    rm -rf src/jellyscope/web/static/dist
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
