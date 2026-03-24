# Repository Guidelines

## Project Structure & Module Organization
This is a FastAPI backend in `app/` and tests in `tests/`.

- `app/main.py` wires the API, middleware, and router registration.
- `app/core/`, `app/models/`, `app/services/`, `app/api/`, and `app/db/` contain business logic, request/response schemas, orchestration, route handlers, and state persistence.
- `tests/` contains pytest suites (examples: `test_health.py`, `test_runs_api.py`).
- `pyproject.toml` defines dependencies and tooling (runtime, dev, and optional extras). `uv.lock` tracks the resolved versions.
- `Dockerfile` supports containerized local execution on port `8000`.

## Build, Test, and Development Commands
- `make install` — create virtual environment and install runtime + dev dependencies with `uv pip install .[dev]`.
- `make fmt` — format with Ruff and compile-check Python files.
- `make lint` — run Ruff lint + format check.
- `make typecheck` — run `mypy` on `app/`.
- `make test` — run full pytest suite.
- `make test-check` — run pytest with coverage checks (`--cov-fail-under=70`).
- `make security` — run Bandit scan for security issues.
- `make ci` — execute `lint`, `typecheck`, `test`, and `security` in one pass.
- Local run (Python env): `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Docker run: `docker build -t aflight-backend . && docker run -p 8000:8000 aflight-backend`

## Coding Style & Naming Conventions
- Target Python 3.12, 4-space indentation, LF line endings.
- Ruff line length: 100 chars.
- Use `snake_case` for functions/variables/files/modules, `PascalCase` for classes, `ALL_CAPS` for constants.
- Prefer explicit imports, clear service boundaries, and small, testable functions.
- Keep API payload/route names explicit and consistent across services and tests.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-cov`, strict config/markers.
- Test files and functions should follow `test_*.py` and `def test_*` naming.
- Keep tests aligned with route behavior and stateful service behavior in `tests/`.
- Run `make test` before pushing, and `make test-check` before merges.

## Commit & Pull Request Guidelines
- This repository currently has no commit history (`master` branch has no commits yet), so use a clear convention such as Conventional Commits:
  - `feat: add ...`
  - `fix: ...`
  - `refactor: ...`
  - `test: ...`
- PRs should include:
  - short summary of behavior changes and rationale
  - test command outputs (`make test`, `make lint`, `make typecheck`)
  - linked issue/task reference when available
  - API changes with examples (request/response examples when routes change)

## Security & Configuration Tips
- Copy `.env.example` to `.env` and set environment values before running locally.
- Default config keys: `AFLIGHT_API_PREFIX`, `AFLIGHT_APP_NAME`, `AFLIGHT_ALLOWED_ORIGINS`.
- Store secrets in environment variables and avoid committing runtime credentials or local DB artifacts.
