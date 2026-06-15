[doc('List recipes in this module')]
default:
    @just --list --justfile {{source_file()}}

[doc('Run linter')]
lint:
    uv run ruff check src/ tests/

[doc('Auto-fix lint issues')]
lint-fix:
    uv run ruff check --fix src/ tests/

[doc('Format code')]
format:
    uv run ruff format src/ tests/

[doc('Check formatting without changes')]
format-check:
    uv run ruff format --check src/ tests/

[doc('Type checking')]
typecheck:
    uv run mypy src/

[doc('Spell check')]
spellcheck:
    uv run codespell src/ tests/ docs/ README.md

[doc('Run tests with coverage')]
test:
    uv run pytest

[doc('Fast test run without coverage')]
test-fast:
    uv run pytest --no-cov -x -q

[doc('Run ALL checks (what CI would run)')]
all: lint format-check typecheck spellcheck test
    @echo "All checks passed."
