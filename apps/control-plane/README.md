# Agent Atlas Control Plane

The backend is the control plane for Agent Atlas. It provides the HTTP API, persists Atlas-owned
state, turns governed intake into governed assets, submits run intent through a neutral
execution-control contract, coordinates datasets and experiment batches, and produces export
artifacts.

Strategically, the backend is moving toward a split where:

- Atlas remains the source of truth for governed assets, datasets, experiments, provenance, and
  exports
- Phoenix is an optional trace inspection backend for experiment-heavy debugging workflows
- immutable artifacts or images and runner orchestration become the execution handoff
- local and Kubernetes carriers remain adapter implementations behind the runner handoff boundary
- external systems such as Inspect AI and E2B integrate only through adapters
- RL integration starts with offline export contracts

For the full-stack workflow, start from the repository root README. Use this document when you are
working directly on the backend service.

## What This Service Owns

Today:

- governed intake, governed-asset catalog, and the starter bootstrap convenience surface
- run creation, lifecycle tracking, and execution dispatch as supporting infrastructure
- background job processing through the worker
- trajectory and trace ingestion and normalization behind backend-owned ports
- dataset CRUD
- experiment fan-out and aggregation
- artifact export metadata and download flow
- local development defaults backed by SQLite

Directionally, the backend will also own:

- stronger dataset and sample identity for RL data workflows
- artifact or image provenance attached to governed assets and exports
- runner backend selection and execution control behind a run contract
- Phoenix-backed trace integration behind backend-owned ports and deep links
- RL-ready export contracts and curation-oriented filtering
- canonical evidence records that stay stable across execution backends

The backend should not become the primary place for:

- raw trace browsing UX
- prompt and evaluator management
- manual-run-first workflows
- experiment analysis features that Phoenix already owns

## Architecture

This backend is a modular monolith built with FastAPI.

- `app/modules/`: feature-level `domain`, `application`, and module-local `adapters`
- `app/execution/`: execution orchestration subsystem for handoff, runner dispatch, and launchers
- `app/agent_tracing/`: in-process trace ingest, export, and read-side backend integration
- `app/data_plane/`: in-process trajectory projection and data-side normalization helpers
- `app/infrastructure/`: cross-feature infrastructure adapters
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
[PLATFORM_MODULES.md](./PLATFORM_MODULES.md). Execution subsystem boundaries are documented in
[EXECUTION_ARCHITECTURE.md](./EXECUTION_ARCHITECTURE.md).

## Local Setup

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
make install
cp .env.example .env
make run-api
```

In a second terminal, start the worker:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
make run-worker
```

The worker requires Redis at `AGENT_ATLAS_EXECUTION_JOB_QUEUE_URL` and will fail fast if nothing is
listening there. The repository root [`Makefile`](/Users/leslie/PycharmProjects/agent-atlas/Makefile)
`make dev` target now starts a local Redis container automatically unless something is already
listening on `127.0.0.1:6379`.

Local defaults:

- API base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- local database: `sqlite:///./.agent-atlas-local.db`
- execution job queue: `redis://127.0.0.1:6379/0`

## Runtime Model

Current runtime model:

- API requests create run records immediately and submit them through `ExecutionControlPort`
- the current in-repo adapters map that contract to Arq-backed execution jobs
- `app/execution/` owns the control-plane to runner handoff and launcher-side orchestration
- `app.worker` is a separate Arq worker process that consumes execution jobs
- run both `make run-api` and `make run-worker` during development if you want runs to advance past
  `queued`

Planned runtime direction:

- governed assets stay managed by Atlas while artifact/image handoff replaces control-plane-local
  runtime assumptions
- execution resolves from the governed asset toward immutable artifact or image references
- runner orchestration is added behind infrastructure ports
- local and Kubernetes execution stay as carrier adapters rather than the product default story
- Inspect AI and E2B stay outside the core model as adapter-backed integrations
- runtime and control-plane trace export flows use OTLP without making Phoenix the runtime
  contract
- experiments, datasets, and exports become the primary product loop while runs remain supporting
  execution records

## Dependency Management

`uv` is the package manager for the backend. `pyproject.toml` and `uv.lock` are the source of
truth.

Main install paths:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
make install
make sync
```

- `make install`: create `.venv` and install dev dependencies
- `make sync`: recreate `.venv` exactly from `uv.lock`
- `make install-export`: sync dev plus optional export dependencies such as Parquet support

The backend environment is locked together with the local contracts and `runner-*` packages through
`uv.lock`; `make sync` does not perform any lock-external `uv pip install` steps.

The production image installs the backend plus local contracts and runner packages via
[Dockerfile](./Dockerfile). Build it from the repository root so those paths are in the Docker
context:

```bash
docker build -f apps/control-plane/Dockerfile .
```

## Configuration

Copy [`.env.example`](./.env.example) to `.env`.

Important settings currently wired in code:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for frontend access
- `AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL`: control-plane state database location
- `AGENT_ATLAS_DATA_PLANE_DATABASE_URL`: data-plane state database location
- `AGENT_ATLAS_OPENAI_API_KEY`: credentials for OpenAI-backed run paths when those paths are selected
- `AGENT_ATLAS_EXECUTION_JOB_BACKEND`: background execution backend (`arq` in product code, `inline` only for tests)
- `AGENT_ATLAS_EXECUTION_JOB_QUEUE_URL`: Redis DSN used by the Arq execution queue
- `AGENT_ATLAS_EXECUTION_JOB_QUEUE_NAME`: Arq queue name used for execution jobs

Planned settings such as runner backend selection or artifact build controls should not be treated
as live product behavior until they are backed by code.

Tracing settings:

- `AGENT_ATLAS_TRACING_OTLP_ENDPOINT`: OTLP collector endpoint used for neutral trace export
- `AGENT_ATLAS_TRACING_PROJECT_NAME`: logical tracing project name
- `AGENT_ATLAS_TRACING_HEADERS`: optional OTLP export headers as JSON
- `AGENT_ATLAS_PHOENIX_BASE_URL`: optional backend-owned Phoenix deep link base URL
- `AGENT_ATLAS_PHOENIX_API_KEY`: optional Phoenix API key used for OTLP export and deeplink
  resolution

Runtime notes:

- Atlas no longer exposes a platform-global runtime-mode switch.
- Real execution is selected through explicit provider, runner, and executor configuration.
- Simulated execution remains a test-owned internal seam rather than a documented product mode.
- Legacy mode symbols are intentionally unsupported and should not be reintroduced:
  `AGENT_ATLAS_RUNTIME_MODE`, `RuntimeMode`, `effective_runtime_mode`, `settings.runtime_mode`,
  `runtime_mode`, and `AGENT_ATLAS_RUNNER_MODE`.

## Developer Commands

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
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

- `make test`: run the backend suite without the coverage gate for fast local verification
- `make test-check`: run the backend coverage gate
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
  - `GET /api/v1/agents/published`
  - `POST /api/v1/agents/imports`
  - `POST /api/v1/agents/starters/claude-code`
  - `POST /api/v1/agents/{agent_id}/validation-runs`
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
- Experiments:
  - `GET /api/v1/experiments`
  - `POST /api/v1/experiments`
  - `GET /api/v1/experiments/{experiment_id}`
  - `POST /api/v1/experiments/{experiment_id}/start`
  - `POST /api/v1/experiments/{experiment_id}/cancel`
  - `GET /api/v1/experiments/{experiment_id}/runs`
  - `PATCH /api/v1/experiments/{experiment_id}/runs/{run_id}`
- Exports:
  - `GET /api/v1/exports`
  - `POST /api/v1/exports`
  - `GET /api/v1/exports/{export_id}`

Product note:

- `runs` remain important backend objects, but they are supporting APIs for eval, provenance, and
  export workflows rather than the center of the product experience
- `POST /api/v1/agents/imports` and `POST /api/v1/agents/starters/claude-code` are two entry
  surfaces into the same governed-intake path; the starter route is a convenience prefill, not a
  separate product lane

Sample datasets for manual import live under `apps/control-plane/datasets/`. The seeded
`fulfillment_ops` dataset is also available as
[`apps/control-plane/datasets/fulfillment-eval-v1.jsonl`](/Users/leslie/PycharmProjects/agent-atlas/apps/control-plane/datasets/fulfillment-eval-v1.jsonl)
so you can upload it through the UI or load it into the database without relying on demo seeding.
The starter walkthrough also has a real code-edit JSONL at
[`apps/control-plane/datasets/claude-code-code-edit-v1.jsonl`](/Users/leslie/PycharmProjects/agent-atlas/apps/control-plane/datasets/claude-code-code-edit-v1.jsonl),
which is designed for the Claude Code starter's mounted sample project instead of the older toy
prompt loop.

## Verification

Typical local verification:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
make lint
make typecheck
make test
make security
```

For the standard backend CI bundle:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/control-plane
make ci
```
