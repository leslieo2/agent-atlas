# Agent Atlas

Agent Atlas is a self-hosted control plane for turning agents and datasets into governed,
RL-ready execution data.

It gives teams one product surface for:

- governing intake into runnable agent assets
- defining datasets, slices, provenance, and export eligibility
- running and comparing experiments over governed assets
- exporting curated offline files for downstream RL or post-training workflows

Atlas is the product center for agent governance, datasets, experiments, and exports. Phoenix
remains the trace and debugging backend. Runner adapters such as Claude Code CLI stay visible, but
they do not become the product itself.

## Product Contract

Atlas is organized around one canonical lifecycle:

`governed intake -> governed asset -> run -> evidence -> export`

That lifecycle maps to the four operator-facing product surfaces:

- `Agents`: intake, validate, and govern runnable assets
- `Datasets`: define dataset identity, slices, provenance, and export eligibility
- `Experiments`: turn governed assets and datasets into runs, compare outcomes, and curate rows
- `Exports`: package curated evidence-backed rows into offline handoff files

What Atlas ingests:

- governed agent intake
- datasets and dataset slices
- run intent against a governed asset + dataset pairing

What Atlas produces:

- governed assets with validation state
- run records and evidence
- curated export artifacts for downstream RL or post-training workflows

## Boundary Rules

- Atlas owns the product model, provenance, curation, and export semantics.
- Phoenix owns raw traces and deep debugging. Atlas links out to Phoenix; it does not rebuild Phoenix as a peer workspace.
- Runner adapters, providers, carriers, and tool integrations stay behind Atlas-owned contracts and provenance fields.
- The README is the public entrypoint. Internal transition history, superseded wording, and deeper architecture debate belong in subsystem docs, not here.

## First Product Loop

The default local operator path is:

1. start the stack with `make dev`
2. open `Agents` and add or govern the first asset
3. open `Datasets` and import a dataset
4. open `Experiments` and run the dataset against the governed asset
5. review evidence, compare outcomes, and curate rows
6. open `Exports` and create an offline handoff file

If this loop works, Atlas is behaving like the product described above.

## Quick Start

From the repository root:

```bash
make install
cp apps/control-plane/.env.example apps/control-plane/.env
cp apps/web/.env.example apps/web/.env.local
make dev
```

Default local endpoints:

- Phoenix: `http://127.0.0.1:6006`
- backend API: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:3000`

`make dev` starts Phoenix through Docker, so make sure Docker Desktop or the Docker daemon is running first.
Stop all local processes together with `Ctrl-C`.

## What Is In This Repository

For contributors, the repository is organized by product and execution ownership:

- `apps/web/`: operator-facing web UI
- `apps/control-plane/`: FastAPI control plane, worker process, feature modules, tests, and
  backend-specific tooling
- `packages/contracts/`: neutral cross-plane contract package
- `runtimes/`: execution-side runtime packages, including shared runner bootstrap and launcher code
- `infra/`, `schemas/`, and `docs/`: deployment assets, shared schemas, and architecture docs
- `Makefile`: root entrypoint for installing dependencies and running the common full-stack
  workflows

`apps/control-plane/app/*` holds in-process control-plane modules, `packages/*` holds shared
libraries, `schemas/*` holds language-neutral definitions, and `runtimes/*` holds execution-side
implementations that should remain downstream of Atlas-owned product semantics.

## Architecture At A Glance

- Control plane: governs intake, assets, runs, evidence, curation, and export records.
- Web app: the operator-facing product UI, organized around `Agents / Datasets / Experiments / Exports`.
- Shared contracts: neutral run/evidence/export boundary types under `packages/contracts/`.
- Execution runtimes: downstream carriers and adapter integrations under `runtimes/`.
- Observability: Phoenix stays as the trace/deep-debug backend behind Atlas-linked evidence.

### Platform Diagram

```text
Web UI (Agents / Datasets / Experiments / Exports)
                    |
               HTTPS / JSON
                    v
Control Plane (Atlas-owned product semantics + neutral run/evidence APIs)
     | run intent            | evidence / query            | product-owned records
     v                       v                             v
Execution Plane      Observability / Eval Plane         Data Plane
     \______________________ Runner / Agent Runtime ______________________/
                               | tool / model / OTLP
                               v
                    Tool Gateway / Model Gateway / Phoenix

Data Plane -------------------------------------------------> Training Plane
```

Use this as the quick mental model:

- the control plane is the product center
- execution and runner layers exist to carry Atlas run intent, not to define Atlas domain objects
- observability backends such as Phoenix project into Atlas evidence instead of becoming the
  product truth
- the data plane is where evidence becomes training-usable data

The full version of this diagram and the corresponding boundary rules live in
[docs/architecture/overview.md](docs/architecture/overview.md).

Use the deeper docs when you need subsystem rules rather than the public entrypoint:

- [prd.md](prd.md)
- [roadmap.md](roadmap.md)
- [docs/architecture/overview.md](docs/architecture/overview.md)
- [docs/architecture/repository-layout.md](docs/architecture/repository-layout.md)
- [docs/architecture/platform-boundaries.md](docs/architecture/platform-boundaries.md)
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
make frontend-e2e
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
- `make frontend-ci`: run hermetic web CI checks from `apps/web/package.json`
- `make frontend-e2e`: run frontend local browser smoke checks
- `make ci`: run both backend and hermetic frontend CI flows

## Environment Configuration

### Backend

Copy `apps/control-plane/.env.example` to `apps/control-plane/.env`.

Key settings currently wired in the backend:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: application name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for local frontend access
- `AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL`: control-plane state database location
- `AGENT_ATLAS_DATA_PLANE_DATABASE_URL`: data-plane state database location
- `AGENT_ATLAS_OPENAI_API_KEY`: OpenAI credentials for OpenAI-backed run paths when selected
- `AGENT_ATLAS_EXECUTION_JOB_BACKEND`: background execution backend (`arq` in product code, `inline` only for tests)
- `AGENT_ATLAS_EXECUTION_JOB_QUEUE_URL`: Redis DSN used by the Arq execution queue
- `AGENT_ATLAS_EXECUTION_JOB_QUEUE_NAME`: Arq queue name used for execution jobs

Planned infrastructure settings such as runner backend selection should not be treated as shipped
until they are backed by code and documented in subsystem docs.

Tracing and deep-link settings:

- `AGENT_ATLAS_TRACING_OTLP_ENDPOINT`
- `AGENT_ATLAS_TRACING_PROJECT_NAME`
- `AGENT_ATLAS_TRACING_HEADERS` (optional JSON map)
- `AGENT_ATLAS_PHOENIX_BASE_URL`
- `AGENT_ATLAS_PHOENIX_API_KEY` (optional)

Legacy runtime-mode names are not supported and should not appear in code or docs:
`AGENT_ATLAS_RUNTIME_MODE`, `RuntimeMode`, `effective_runtime_mode`, `settings.runtime_mode`,
`runtime_mode`, and `AGENT_ATLAS_RUNNER_MODE`.

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
npm run verify:full
```

Additional frontend commands:

- `npm run format`
- `npm run format:check`
- `npm run lint:fix`
- `npm run test:coverage`
- `npm run test:e2e`
- `npm run verify:ci`
- `npm run verify`
- `npm run verify:full`
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

If you also want browser smoke coverage against a local backend stack:

```bash
make frontend-e2e
```

If you are working in only one subproject, use the subsystem-local CI entrypoint:

- backend: `cd apps/control-plane && make ci`
- frontend: `cd apps/web && npm run ci`

Use the local full frontend verification bundle only when you explicitly want Playwright against a
local backend:

- frontend: `cd apps/web && npm run verify:full`

## Where To Go Next

- Product direction and boundaries: [prd.md](prd.md), [roadmap.md](roadmap.md)
- Backend runtime, API surface, and environment details: [apps/control-plane/README.md](apps/control-plane/README.md)
- Backend architecture and dependency rules: [apps/control-plane/ARCHITECTURE.md](apps/control-plane/ARCHITECTURE.md)
- Frontend setup, testing, and product surfaces: [apps/web/README.md](apps/web/README.md)
- Frontend architecture rules: [apps/web/ARCHITECTURE.md](apps/web/ARCHITECTURE.md)
- Repository conventions for contributors and agents: [apps/control-plane/AGENTS.md](apps/control-plane/AGENTS.md),
  [apps/web/AGENTS.md](apps/web/AGENTS.md)
