# Agent Atlas

Agent Atlas is a self-hosted control plane for turning published agents and datasets into governed
RL-ready execution data.

It combines:

- a FastAPI backend that owns agent publication, dataset identity, eval orchestration, provenance,
  and export contracts
- a Next.js frontend that exposes the operator-facing RL data control plane
- a Phoenix-first debugging model where raw traces, prompts, playground flows, and experiment
  analysis live outside Atlas

## What Is In This Repository

- `apps/web/`: operator-facing web UI
- `apps/control-plane/`: FastAPI control plane, worker process, feature modules, tests, and
  backend-specific tooling
- planned product-plane services such as `apps/data-ingestion/`, `apps/export-worker/`,
  `apps/eval-worker/`, `apps/executor-gateway/`, and `apps/data-plane-api/`: target landing zones
  for the next split, not directories that exist in this checkout today
- `packages/contracts/`: neutral cross-plane contract package
- `runtimes/`: execution-side runtime packages, including shared runner bootstrap and launcher code
- `infra/`, `schemas/`, and `docs/`: deployment assets, shared schemas, and architecture docs
- `Makefile`: root entrypoint for installing dependencies and running the common full-stack
  workflows

Repository placement follows one rule: place code by execution ownership, not by conceptual name.
`apps/control-plane/app/*` holds in-process control-plane subsystems, `packages/*` holds shared
libraries, `schemas/*` holds language-neutral definitions, and `runtimes/*` holds execution-side
implementations that should evolve outside the control-plane process.

## Current Capability Snapshot

What exists today:

- repository-local agent discovery and publish / unpublish workflow
- worker-backed execution behind a neutral run-control contract
- dataset management and dataset-driven eval jobs
- artifact export for downstream analysis
- legacy run, trajectory, and playground surfaces from the earlier workbench story

What is directional, not yet shipped:

- immutable artifact or image-backed publication
- richer curation-first export contracts for RL workflows
- product-level removal of Atlas surfaces that overlap with Phoenix
- Docker or remote runner orchestration beyond the current local-first path

## Product Direction

Agent Atlas is not trying to become another hosted observability or experimentation product.

The product boundary is:

- Agent Atlas owns published agent governance, datasets, experiments, provenance, curation, and
  export semantics
- Phoenix owns raw traces, playground, prompts, evaluators, and experiment analysis
- RL integration starts with offline export first, not direct training orchestration

The target first-class Atlas surfaces are:

- `Agents`
- `Datasets`
- `Experiments`
- `Exports`

This means the long-term shape is:

- repo-local discovery and validation
- governed publication with artifact, image, and runner provenance
- dataset and sample identity for RL data production
- eval-driven batch execution and comparison
- Phoenix-linked debugging instead of Atlas-native trace tooling
- RL-ready offline export

## Platform Architecture

The product should be described first as a layered platform, not as one giant hexagonal
application.

The platform planes are:

- control plane: governs datasets, experiments, runs, provenance, curation, and
  export contracts
- execution plane: runs agents in isolated carriers such as local workers, containers, or
  Kubernetes jobs
- observability and eval plane: collects telemetry, stores raw traces, and supports debugging and
  comparison
- data plane: normalizes trajectories, artifacts, labels, and lineage into training-usable data
- training plane: filters, transforms, and exports offline RL or post-training datasets

Hexagonal architecture is still useful, but only locally:

- use it inside control-plane and core business services where Atlas-owned semantics must stay
  stable while backends change
- do not use it as the primary mental model for the whole platform topology
- do not force execution orchestration, telemetry pipelines, or high-throughput data processing
  into a pure ports-and-adapters shape when state-machine, event-driven, or data-pipeline designs
  fit better

## Architecture At A Glance

- Control plane: a modular monolith built with FastAPI. HTTP routes stay thin, feature logic lives
  under `apps/control-plane/app/modules`, infrastructure adapters live under
  `apps/control-plane/app/infrastructure`, and wiring happens in
  `apps/control-plane/app/bootstrap/container.py`.
- Web app: a layered Next.js App Router app. Route entrypoints live in `apps/web/app`, while
  product code follows `app -> widgets -> features -> entities -> shared` in `apps/web/src`.
- Shared contracts: the long-term neutral boundary for `RunSpec`, event envelopes, artifact
  manifests, and related cross-plane contracts lives under `packages/contracts/`.
- Planned packages and worker apps described elsewhere in the docs are directional landing zones
  unless the directory exists in the repository today.
- External backend direction: Atlas keeps control-plane truth while Phoenix remains the required
  analysis plane for raw traces and experiment-heavy debugging workflows.

Use the subsystem docs for the full architecture rules:

- [prd.md](prd.md)
- [roadmap.md](roadmap.md)
- [docs/architecture/repository-layout.md](docs/architecture/repository-layout.md)
- [apps/control-plane/README.md](apps/control-plane/README.md)
- [apps/control-plane/ARCHITECTURE.md](apps/control-plane/ARCHITECTURE.md)
- [apps/control-plane/PLATFORM_MODULES.md](apps/control-plane/PLATFORM_MODULES.md)
- [apps/control-plane/AGENTS.md](apps/control-plane/AGENTS.md)
- [apps/web/README.md](apps/web/README.md)
- [apps/web/ARCHITECTURE.md](apps/web/ARCHITECTURE.md)
- [apps/web/AGENTS.md](apps/web/AGENTS.md)

## Prerequisites

Install these before working in the repository:

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) for backend environment and dependency management
- Node.js and `npm` for the frontend
- Docker if you want `make dev` to launch the local Phoenix server for you

## Quick Start

From the repository root:

```bash
make install
cp apps/control-plane/.env.example apps/control-plane/.env
cp apps/web/.env.example apps/web/.env.local
make dev
```

This starts the local stack with the default ports:

- Phoenix: `http://127.0.0.1:6006`
- backend API: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:3000`

Stop all three development processes together with `Ctrl-C`.
`make dev` starts Phoenix through Docker, so make sure Docker Desktop or the Docker daemon is running first.

## Local Development Workflow

`make dev` starts:

- the local Phoenix server
- the backend API server
- the backend worker process
- the frontend development server

The worker is required if you want queued runs to progress beyond `queued`. If you only start the
API, run records can still be created, but background execution will not advance.

Useful root commands:

```bash
make help
make install
make dev
make lint
make typecheck
make test
make build
make backend-ci
make frontend-ci
make ci
```

What they do:

- `make install`: install backend and frontend dependencies
- `make dev`: start Phoenix, backend API, backend worker, and frontend dev server together
- `make lint`: run backend and frontend lint checks
- `make typecheck`: run backend mypy and frontend TypeScript checks
- `make test`: run backend pytest and frontend Vitest suites
- `make build`: run the frontend production build
- `make backend-ci`: run control-plane CI checks from `apps/control-plane/Makefile`
- `make frontend-ci`: run web CI checks from `apps/web/package.json`
- `make ci`: run both backend and frontend CI flows

## Environment Configuration

### Backend

Copy `apps/control-plane/.env.example` to `apps/control-plane/.env`.

Key settings currently wired in the backend:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: application name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for local frontend access
- `AGENT_ATLAS_RUNTIME_MODE`: provider execution behavior (`auto`, `live`, `mock`)
- `AGENT_ATLAS_DATABASE_URL`: SQLite database location for local state
- `AGENT_ATLAS_SEED_DEMO`: whether demo data is seeded on startup
- `AGENT_ATLAS_OPENAI_API_KEY` or `OPENAI_API_KEY`: OpenAI credentials for live mode

Planned infrastructure settings such as runner backend selection should not be treated as shipped
until they are backed by code and documented in subsystem docs.

Phoenix-backed tracing is now required behind backend-owned settings:

- `AGENT_ATLAS_PHOENIX_BASE_URL`
- `AGENT_ATLAS_PHOENIX_OTLP_ENDPOINT`
- `AGENT_ATLAS_PHOENIX_PROJECT_NAME`
- `AGENT_ATLAS_PHOENIX_API_KEY` (optional)

### Frontend

Copy `apps/web/.env.example` to `apps/web/.env.local`.

Key setting:

- `NEXT_PUBLIC_API_BASE_URL`: browser-visible backend base URL, defaulting to
  `http://127.0.0.1:8000`

## Work By Subproject

Use the root workflow when you want the standard local stack. Drop into a subproject when you need
more focused commands.

### Backend

```bash
cd apps/control-plane
make install
make run-api
make run-worker
make lint
make typecheck
make test
make security
make ci
```

Additional backend commands:

- `make sync`: recreate the virtualenv and install from `uv.lock`
- `make test-check`: run pytest with coverage output
- `make test-unit`: run unit tests only
- `make test-integration`: run integration tests only
- `make test-e2e`: run backend end-to-end tests
- `make contract-sync`: regenerate the frontend contract from backend sources
- `make contract-check`: verify the generated frontend contract is up to date

Swagger UI is available at `http://127.0.0.1:8000/docs`.

### Frontend

```bash
cd apps/web
npm install
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
npm run ci
```

Additional frontend commands:

- `npm run format`
- `npm run format:check`
- `npm run lint:fix`
- `npm run test:coverage`
- `npm run test:e2e`
- `npm run verify`
- `npm run check`

## Testing And CI

Recommended local verification before opening a PR:

```bash
make test
make lint
make typecheck
```

For broader verification:

```bash
make ci
```

If you are working in only one subproject, use the subsystem-local CI entrypoint:

- backend: `cd apps/control-plane && make ci`
- frontend: `cd apps/web && npm run ci`

## Where To Go Next

- Product direction and boundaries: [prd.md](prd.md), [roadmap.md](roadmap.md)
- Backend runtime, API surface, and environment details: [apps/control-plane/README.md](apps/control-plane/README.md)
- Backend architecture and dependency rules: [apps/control-plane/ARCHITECTURE.md](apps/control-plane/ARCHITECTURE.md)
- Frontend setup, testing, and product surfaces: [apps/web/README.md](apps/web/README.md)
- Frontend architecture rules: [apps/web/ARCHITECTURE.md](apps/web/ARCHITECTURE.md)
- Repository conventions for contributors and agents: [apps/control-plane/AGENTS.md](apps/control-plane/AGENTS.md),
  [apps/web/AGENTS.md](apps/web/AGENTS.md)
