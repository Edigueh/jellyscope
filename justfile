mod docker
mod check

[doc('List recipes')]
default:
    @just --list

[doc('Install all dependencies including dev + pre-commit hooks')]
install:
    uv sync --extra dev
    uv run pre-commit install

[doc('Start the development server')]
serve:
    uv run jellyscope --data-dir data

[doc('Start with auto-reload (development)')]
serve-dev:
    uv run uvicorn jellyscope.web:create_app --factory --reload --host 127.0.0.1 --port 5000

[doc('Clean build artifacts')]
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
