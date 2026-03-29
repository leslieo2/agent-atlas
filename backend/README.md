# Agent Atlas Backend

The backend is the control plane for Agent Atlas. It provides the HTTP API, persists Atlas-owned
state, submits run intent through a neutral execution-control contract, manages repository-local
agent publication, coordinates datasets and eval jobs, and produces export artifacts.

Strategically, the backend is moving toward a split where:

- Atlas remains the source of truth for published agents, datasets, eval jobs, provenance, and
  exports
- Phoenix is the required backend for raw trace inspection and experiment-heavy debugging workflows
- immutable artifacts or images and runner orchestration become the execution handoff
- RL integration starts with offline export contracts

For the full-stack workflow, start from the repository root README. Use this document when you are
working directly on the backend service.

## What This Service Owns

Today:

- repository-local agent discovery and publication
- run creation, lifecycle tracking, and execution dispatch as supporting infrastructure
- background job processing through the worker
- trajectory and trace ingestion and normalization behind backend-owned ports
- dataset CRUD
- eval job fan-out and aggregation
- artifact export metadata and download flow
- local development defaults backed by SQLite

Directionally, the backend will also own:

- stronger dataset and sample identity for RL data workflows
- artifact or image provenance attached to published agents and exports
- runner backend selection and execution control behind a run contract
- Phoenix-backed trace integration behind backend-owned ports and deep links
- RL-ready export contracts and curation-oriented filtering

The backend should not become the primary place for:

- raw trace browsing UX
- prompt and evaluator management
- manual-run-first workflows
- experiment analysis features that Phoenix already owns

## Architecture

This backend is a modular monolith built with FastAPI.

- `app/api/routes/`: HTTP entrypoints
- `app/modules/`: feature-level application and domain logic
- `app/infrastructure/`: repositories and outbound adapters
- `app/bootstrap/container.py`: composition root

This is the internal architecture of the control-plane backend, not the architecture of the whole
product platform.

At the product level, Atlas should still be described as a layered system with control,
execution, observability or eval, data, and training planes. Inside this backend, ports and
adapters are useful because they keep Atlas-owned semantics stable while runner, trace, and
storage implementations change.

Read the full architecture rules in [ARCHITECTURE.md](./ARCHITECTURE.md). Contributor and layering
guidance lives in [AGENTS.md](./AGENTS.md). Module ownership and the split between hexagonal
control-plane code and non-hex execution or pipeline code is documented in
[PLATFORM_MODULES.md](./PLATFORM_MODULES.md).

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

Current runtime model:

- API requests create run records immediately and submit them through `ExecutionControlPort`
- the current local backend maps that contract to queued worker tasks
- `app.worker` is a separate process that claims queued jobs and executes them
- run both `make run-api` and `make run-worker` during development if you want runs to advance past
  `queued`

Planned runtime direction:

- published agents remain repo-local and governed by Atlas
- execution resolves from published snapshot toward immutable artifact or image references
- runner orchestration is added behind infrastructure ports
- raw trace and evaluation observability run through Phoenix without making Phoenix the control
  plane
- eval jobs, datasets, and exports become the primary product loop while runs remain supporting
  execution records

## Dependency Management

`uv` is the package manager for the backend. `pyproject.toml` and `uv.lock` are the source of
truth.

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

Important settings currently wired in code:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for frontend access
- `AGENT_ATLAS_RUNTIME_MODE`: provider execution behavior (`auto`, `live`, `mock`)
- `AGENT_ATLAS_DATABASE_URL`: SQLite database location
- `AGENT_ATLAS_SEED_DEMO`: whether to seed demo data on startup
- `AGENT_ATLAS_OPENAI_API_KEY` or `OPENAI_API_KEY`: credentials for live mode
- `AGENT_ATLAS_WORKER_NAME`: optional worker name override
- `AGENT_ATLAS_WORKER_POLL_INTERVAL_SECONDS`: worker polling interval
- `AGENT_ATLAS_WORKER_TASK_LEASE_SECONDS`: worker task lease duration

Planned settings such as runner backend selection or artifact build controls should not be treated
as live product behavior until they are backed by code.

Phoenix tracing is now required in code:

- `AGENT_ATLAS_PHOENIX_BASE_URL`: backend-owned Phoenix deep link base URL
- `AGENT_ATLAS_PHOENIX_OTLP_ENDPOINT`: OTLP collector endpoint used by the Phoenix SDK
- `AGENT_ATLAS_PHOENIX_PROJECT_NAME`: project name used for Atlas-exported traces
- `AGENT_ATLAS_PHOENIX_API_KEY`: optional API key for Phoenix export/query access
- `AGENT_ATLAS_PHOENIX_QUERY_LIMIT`: read-side span fetch cap for run trace reconstruction

Runtime mode notes:

- `AGENT_ATLAS_RUNTIME_MODE=mock`: always simulate execution
- `AGENT_ATLAS_RUNTIME_MODE=auto`: use live execution when an API key is configured, otherwise
  fallback to mock
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
- Agents:
  - `GET /api/v1/agents`
  - `GET /api/v1/agents/discovered`
  - `POST /api/v1/agents/{agent_id}/publish`
  - `POST /api/v1/agents/{agent_id}/unpublish`
- Runs:
  - `GET /api/v1/runs`
  - `POST /api/v1/runs`
  - `GET /api/v1/runs/{run_id}`
  - `POST /api/v1/runs/{run_id}/terminate`
  - `GET /api/v1/runs/{run_id}/trajectory`
  - `GET /api/v1/runs/{run_id}/traces`
- Datasets:
  - `GET /api/v1/datasets`
  - `POST /api/v1/datasets`
- Eval jobs:
  - `GET /api/v1/eval-jobs`
  - `POST /api/v1/eval-jobs`
  - `GET /api/v1/eval-jobs/{eval_job_id}`
  - `GET /api/v1/eval-jobs/{eval_job_id}/samples`
- Artifacts:
  - `GET /api/v1/artifacts`
  - `POST /api/v1/artifacts/export`
  - `GET /api/v1/artifacts/{artifact_id}`
- Traces:
  - `POST /api/v1/traces/normalize`
  - `POST /api/v1/traces/ingest`

Product note:

- `runs` and `traces` remain important backend objects, but they are supporting APIs for eval,
  provenance, and export workflows rather than the center of the product experience

Sample datasets for manual import live under `backend/datasets/`. The seeded `fulfillment_ops`
dataset is also available as
[`backend/datasets/fulfillment-eval-v1.jsonl`](/Users/leslie/PycharmProjects/agent-atlas/backend/datasets/fulfillment-eval-v1.jsonl)
so you can upload it through the UI or load it into the database without relying on demo seeding.

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
