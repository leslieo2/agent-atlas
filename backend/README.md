# Agent Flight Recorder Backend

Backend service for the PRD v1 workbench, implemented with FastAPI.

Architecture overview: see `ARCHITECTURE.md`.

## What this project includes

- Run orchestration and lifecycle tracking
- OpenAI Agents SDK runtime integration
- Trajectory/trace ingestion and normalisation
- Artifact export API (JSONL / Parquet when available)
- In-memory seed state to get started quickly (no external services required)

## Run locally

```bash
cd /Users/leslie/PycharmProjects/agent-flight-recorder/backend
uv venv .venv
source .venv/bin/activate
uv pip install ".[dev]"
make run-api
```

In a second terminal, start the worker process:

```bash
cd /Users/leslie/PycharmProjects/agent-flight-recorder/backend
source .venv/bin/activate
make run-worker
```

### Dependency strategy (recommended)

Current repo policy: `uv` is the package manager, and `pyproject.toml` + `uv.lock` are the source of truth.

- Install runtime + dev deps:

```bash
cd backend
uv venv .venv
uv pip install ".[dev]"
```

- Optional export feature dependencies:

```bash
uv pip install ".[export]"
```

- For production image, `backend/Dockerfile` installs from `pyproject.toml` directly.

## Developer Commands

```bash
cd /Users/leslie/PycharmProjects/agent-flight-recorder/backend
make install   # uv venv + install dev deps
make sync      # uv venv + reproducible install from uv.lock
make lint      # ruff lint/format checks
make typecheck # mypy
make test      # pytest
make test-check # pytest with coverage
make security  # bandit
make run-api   # start FastAPI server
make run-worker # start background worker for queued runs
make ci        # lint + typecheck + test + security
```

## Environment

Copy `backend/.env.example` to `backend/.env` for local defaults.

- `AFLIGHT_RUNTIME_MODE=mock` forces simulated execution.
- `AFLIGHT_RUNTIME_MODE=auto` uses live execution when an OpenAI key is configured and mock otherwise.
- `AFLIGHT_RUNTIME_MODE=live` requires a real OpenAI key and does not seed demo data by default.
- `AFLIGHT_SEED_DEMO` overrides the default seed behavior when you explicitly want demo records on or off.
- `OPENAI_API_KEY` and `AFLIGHT_OPENAI_API_KEY` are both supported for live mode.

## Runtime model

- API requests create `run` records immediately and enqueue background tasks in SQLite.
- `app.worker` is a separate process that claims queued tasks and executes them.
- Run both the API server and the worker during local development if you want runs to progress past `queued`.

## API

- Health: `GET /health`
- Runs: `GET /api/v1/runs`, `POST /api/v1/runs`, `GET /api/v1/runs/{run_id}`
- Trajectories: `GET /api/v1/runs/{run_id}/trajectory`
- Datasets: `GET /api/v1/datasets`, `POST /api/v1/datasets`
- Artifacts: `POST /api/v1/artifacts/export`, `GET /api/v1/artifacts/{artifact_id}`
- Traces: `POST /api/v1/traces/ingest`

Swagger UI: `http://localhost:8000/docs`
