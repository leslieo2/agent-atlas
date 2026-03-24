.PHONY: install install-export sync lint fmt typecheck test test-check security ci

install:
	uv venv --clear .venv
	uv pip install --python .venv/bin/python3 ".[dev]"

sync:
	uv venv --clear .venv
	uv sync --project .

install-export:
	uv pip install --python .venv/bin/python3 ".[export]"

fmt:
	uv run ruff format app tests
	uv run python -m compileall -q app tests

lint:
	uv run ruff check app tests
	uv run ruff format --check app tests

typecheck:
	uv run mypy app

test:
	uv run pytest

test-check:
	uv run pytest --cov=app --cov-report=term-missing

security:
	uv run bandit -r app -x tests

ci:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) security
