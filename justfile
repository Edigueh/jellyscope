# List recipes
default:
    @just --list

# Install all dependencies including dev
install:
    uv sync --extra dev
    uv run pre-commit install

# Run linter
lint:
    uv run ruff check src/ tests/

# Auto-fix lint issues
lint-fix:
    uv run ruff check --fix src/ tests/

# Format code
format:
    uv run ruff format src/ tests/

# Check formatting without changes
format-check:
    uv run ruff format --check src/ tests/

# Type checking
typecheck:
    uv run mypy src/

# Run tests with coverage
test:
    uv run pytest

# Fast test run without coverage
test-fast:
    uv run pytest --no-cov -x -q

# Spell check
spellcheck:
    uv run codespell src/ tests/ docs/ README.md

# Run ALL checks (what CI would run)
check: lint format-check typecheck spellcheck test
    @echo "All checks passed."

# Start the development server
serve:
    uv run jellyscope --data-dir data

# Start with auto-reload (development)
serve-dev:
    uv run uvicorn jellyscope.web:create_app --factory --reload --host 127.0.0.1 --port 5000

# Build the Docker image (tagged with pyproject version)
docker-build:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose build

# Start the containerized service (detached)
docker-up:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose up -d

# Stop and remove the containerized service
docker-down:
    docker compose down

# Tail logs from the running container
docker-logs:
    docker compose logs -f jellyscope

# Restart container without rebuild (env/state reset only — does NOT pick up code changes)
docker-restart:
    docker compose restart jellyscope

# Rebuild image and recreate container (picks up code changes; uses layer cache)
docker-reload:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose up -d --build

# Start dev container with bind-mounted src and uvicorn --reload (hot reload)
docker-dev:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Clean build artifacts
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
