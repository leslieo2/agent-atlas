# Agent Flight Recorder Backend

Backend service for the PRD v1 workbench, implemented with FastAPI.

Architecture overview: see `ARCHITECTURE.md`.

## What this project includes

- Run orchestration and lifecycle tracking
- Adapter registry for OpenAI Agents SDK / LangChain / MCP
- Trajectory/trace ingestion and normalisation
- Step replay API
- Evaluation job orchestration (rule + judge score simulation + tool success simulation)
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
make run-worker # start background worker for queued runs/evals
make ci        # lint + typecheck + test + security
```

## Runtime model

- API requests create `run` and `eval job` records immediately and enqueue background tasks in SQLite.
- `app.worker` is a separate process that claims queued tasks and executes them.
- Run both the API server and the worker during local development if you want runs and evals to progress past `queued`.

## API

- Health: `GET /health`
- Runs: `GET /api/v1/runs`, `POST /api/v1/runs`, `GET /api/v1/runs/{run_id}`
- Trajectories: `GET /api/v1/runs/{run_id}/trajectory`
- Replays: `POST /api/v1/replays`, `GET /api/v1/replays/{replay_id}`
- Datasets: `GET /api/v1/datasets`, `POST /api/v1/datasets`
- Eval jobs: `POST /api/v1/eval-jobs`, `GET /api/v1/eval-jobs/{job_id}`
- Artifacts: `POST /api/v1/artifacts/export`, `GET /api/v1/artifacts/{artifact_id}`
- Traces: `POST /api/v1/traces/ingest`
- Adapters: `GET /api/v1/adapters`

Swagger UI: `http://localhost:8000/docs`
