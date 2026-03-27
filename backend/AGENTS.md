# Repository Guidelines

## Project Structure & Module Organization
This backend is a FastAPI service rooted in `app/`. Feature code lives under `app/modules/<feature>/` and is split into `contracts`, `application`, and `domain` layers. Shared wiring and cross-cutting concerns live in `app/api`, `app/bootstrap`, `app/core`, `app/db`, and `app/infrastructure`. Tests live in `tests/` and follow backend features rather than frontend-style colocated specs. Keep generated artifacts such as `.venv/`, `.uv_cache/`, and `coverage.xml` out of commits.

## Build, Test, and Development Commands
Run commands from `backend/`.

- `make install`: create `.venv` and install runtime + dev dependencies.
- `make sync`: recreate `.venv` from `uv.lock` for a reproducible environment.
- `make fmt`: format code with Ruff and verify Python files compile.
- `make lint`: run Ruff lint and format checks.
- `make typecheck`: run mypy against `app/`.
- `make test`: run the full pytest suite with coverage defaults.
- `make test-check`: run pytest with terminal coverage reporting.
- `make security`: run Bandit against `app/`.
- `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`: start the API locally.

## Coding Style & Naming Conventions
Use Python 3.12+, 4-space indentation, LF line endings, double quotes, and a 100-character line limit. Ruff handles formatting and import ordering; mypy enforces type discipline. Use `snake_case` for modules, functions, and variables, and `PascalCase` for classes. Keep API payload mapping explicit and deterministic; avoid hidden schema inference.

## Testing Guidelines
Pytest is the test runner. Put tests in `tests/` with names like `test_runs_api.py`. Use markers intentionally: `unit`, `integration`, and `e2e`. The default pytest config enforces `--cov=app` with `--cov-fail-under=70`, so new work should maintain or improve coverage. Use `make test`, or narrower targets such as `make test-unit` and `make test-integration` during development.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commits such as `feat:`; continue with `feat:`, `fix:`, `refactor:`, and `test:`. PRs should explain what changed, why it changed, and any impacted endpoints or flows. Include command results for `make lint`, `make typecheck`, and `make test`. For API changes, add example request/response payloads.

## Security & Configuration Tips
Use `uv` as the package manager and treat `pyproject.toml` plus `uv.lock` as the source of truth. Configure local environment variables before running the service, and never commit secrets, local dumps, or generated files.
