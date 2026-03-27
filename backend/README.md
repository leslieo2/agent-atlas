# Agent Atlas Backend

The backend is the control plane for the self-hosted Agent Atlas workbench. It provides the HTTP API, persists local state, queues and executes runs, ingests traces, manages datasets, and produces export artifacts.

For the full-stack workflow, start from the repository root README. Use this document when you are working directly on the backend service.

## What This Service Owns

- run creation, lifecycle tracking, and execution dispatch
- background job processing through the worker
- trajectory and trace ingestion and normalization
- dataset CRUD
- artifact export metadata and download flow
- local development defaults backed by SQLite

## Architecture

This backend is a modular monolith built with FastAPI.

- `app/api/routes/`: HTTP entrypoints
- `app/modules/`: feature-level application and domain logic
- `app/infrastructure/`: repositories and outbound adapters
- `app/bootstrap/container.py`: composition root

Read the full architecture rules in [ARCHITECTURE.md](./ARCHITECTURE.md). Contributor and layering guidance lives in [AGENTS.md](./AGENTS.md).

## Local Setup

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make install
cp .env.example .env
make run-api
```

In a second terminal, start the worker:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make run-worker
```

Local defaults:

- API base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- local database: `sqlite:///./.agent-atlas-local.db`

## Runtime Model

- API requests create run records immediately and enqueue work in SQLite-backed local state.
- `app.worker` is a separate process that claims queued jobs and executes them.
- Run both `make run-api` and `make run-worker` during development if you want runs to advance past `queued`.

## Dependency Management

`uv` is the package manager for the backend. `pyproject.toml` and `uv.lock` are the source of truth.

Main install paths:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make install
make sync
```

- `make install`: create `.venv` and install dev dependencies
- `make sync`: create `.venv` and install from `uv.lock`
- `make install-export`: install optional export dependencies such as Parquet support

The production image installs from `pyproject.toml` via [Dockerfile](./Dockerfile).

## Configuration

Copy [`.env.example`](./.env.example) to `.env`.

Important settings:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for frontend access
- `AGENT_ATLAS_RUNNER_MODE`: execution carrier selection (`auto`, `local`, `docker`, `mock`)
- `AGENT_ATLAS_RUNTIME_MODE`: provider execution behavior (`auto`, `live`, `mock`)
- `AGENT_ATLAS_DATABASE_URL`: SQLite database location
- `AGENT_ATLAS_SEED_DEMO`: whether to seed demo data on startup
- `AGENT_ATLAS_RUNNER_IMAGE`: Docker image used when `AGENT_ATLAS_RUNNER_MODE=docker`
- `AGENT_ATLAS_OPENAI_API_KEY` or `OPENAI_API_KEY`: credentials for live mode

Runtime mode notes:

- `AGENT_ATLAS_RUNTIME_MODE=mock`: always simulate execution
- `AGENT_ATLAS_RUNTIME_MODE=auto`: use live execution when an API key is configured, otherwise fallback to mock
- `AGENT_ATLAS_RUNTIME_MODE=live`: require a real API key and disable implicit demo behavior

## Developer Commands

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make install
make sync
make lint
make fmt
make typecheck
make test
make test-check
make security
make run-api
make run-worker
make ci
```

Additional focused commands:

- `make test-unit`
- `make test-integration`
- `make test-e2e`
- `make test-e2e-live`
- `make contract-sync`
- `make contract-check`

## API Surface

Current backend endpoints include:

- Health: `GET /health`
- Runs: `GET /api/v1/runs`, `POST /api/v1/runs`, `GET /api/v1/runs/{run_id}`
- Trajectory: `GET /api/v1/runs/{run_id}/trajectory`
- Datasets: `GET /api/v1/datasets`, `POST /api/v1/datasets`
- Artifacts: `POST /api/v1/artifacts/export`, `GET /api/v1/artifacts/{artifact_id}`
- Traces: `POST /api/v1/traces/ingest`

Sample datasets for manual import live under `backend/datasets/`. The seeded `fulfillment_ops`
dataset is also available as [`backend/datasets/fulfillment-eval-v1.jsonl`](/Users/leslie/PycharmProjects/agent-atlas/backend/datasets/fulfillment-eval-v1.jsonl) so you can upload it through the UI or load it into the database without relying on demo seeding.

## Verification

Typical local verification:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make lint
make typecheck
make test
make security
```

For the standard backend CI bundle:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/backend
make ci
```
