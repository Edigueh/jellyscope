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

# Build the Docker image
docker-build:
    docker compose build

# Seed the jellyscope-data volume from local ./data (run once)
docker-seed:
    docker run --rm -v jellyscope-data:/data -v "$PWD/data":/src alpine sh -c "cp -r /src/. /data/"

# Start the containerized service (detached)
docker-up:
    docker compose up -d

# Stop and remove the containerized service
docker-down:
    docker compose down

# Tail logs from the running container
docker-logs:
    docker compose logs -f jellyscope

# Clean build artifacts
clean:
    rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
