.PHONY: install lint lint-fix format format-check typecheck test test-fast check spellcheck serve serve-dev clean

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

# Run ALL checks (what CI would run)
check: lint format-check typecheck spellcheck test
	@echo "All checks passed."

# Spell check
spellcheck:
	uv run codespell src/ tests/ docs/ README.md

# Start the development server
serve:
	uv run jellyscope --data-dir data

# Start with auto-reload (development)
serve-dev:
	uv run uvicorn jellyscope.web:create_app --factory --reload --host 127.0.0.1 --port 5000

# Clean build artifacts
clean:
	rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
