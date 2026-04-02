.PHONY: install install-export sync lint fmt typecheck test test-unit test-integration test-e2e test-e2e-live test-tdd-unit test-tdd-integration test-check security contract-sync contract-check run-api run-worker ci

install:
	rm -rf .venv
	uv sync --extra dev

sync:
	rm -rf .venv
	uv sync --frozen --extra dev

install-export:
	uv sync --extra dev --extra export

fmt:
	uv run --extra dev ruff format app tests
	uv run --extra dev python -m compileall -q app tests

lint:
	uv run --extra dev ruff check app tests
	uv run --extra dev ruff format --check app tests

typecheck:
	uv run --extra dev mypy app

test:
	uv run --extra dev pytest

test-unit:
	uv run --extra dev pytest -m unit --no-cov

test-integration:
	uv run --extra dev pytest -m integration

test-e2e:
	uv run --extra dev pytest -m e2e

test-e2e-live:
	AGENT_ATLAS_LIVE_TESTS=1 AGENT_ATLAS_RUNTIME_MODE=live AGENT_ATLAS_RUNNER_MODE=local AGENT_ATLAS_SEED_DEMO=false AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL=sqlite:///$(CURDIR)/.agent-atlas-pytest-live-control.db AGENT_ATLAS_DATA_PLANE_DATABASE_URL=sqlite:///$(CURDIR)/.agent-atlas-pytest-live-data.db uv run --extra dev pytest tests/e2e/test_live_smoke.py --no-cov

test-tdd-unit:
	uv run --extra dev pytest -m unit --no-cov -x --ff

test-tdd-integration:
	uv run --extra dev pytest -m integration -x --ff

test-check:
	uv run --extra dev pytest --cov=app --cov-report=term-missing

security:
	@if [ -f bandit-baseline.json ]; then \
		uv run --extra dev bandit -r app -x tests -b bandit-baseline.json; \
	else \
		uv run --extra dev bandit -r app -x tests; \
	fi

contract-sync:
	uv run python scripts/generate_frontend_contract.py

contract-check:
	uv run python scripts/generate_frontend_contract.py --check

run-api:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	uv run python -m app.worker

ci:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) security
