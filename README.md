# Agent Atlas

Agent Atlas is a self-hosted agent workbench for running, observing, and evaluating agent workflows on your own infrastructure. It combines a FastAPI backend that manages runs, traces, datasets, artifacts, and execution orchestration with a Next.js frontend for exploring and operating that workflow.

## What Is In This Repository

- `backend/`: FastAPI service, worker process, feature modules, backend tests, and backend-specific tooling.
- `frontend/`: Next.js App Router application, layered product code, and frontend tests.
- `Makefile`: root entrypoint for installing dependencies and running the common full-stack workflows.

## Current Capability Snapshot

Current capabilities cover the core workbench loop:

- create and inspect runs
- process queued work through a background worker
- ingest and view trajectory and trace data
- manage datasets
- export artifacts
- operate the workbench UI through the run dashboard, trajectory viewer, and playground

At the API level, the backend currently exposes health, runs, trajectories, datasets, artifacts, and trace ingestion endpoints.

## Architecture At A Glance

- Backend: a modular monolith built with FastAPI. HTTP routes stay thin, feature logic lives under `backend/app/modules`, infrastructure adapters live under `backend/app/infrastructure`, and wiring happens in `backend/app/bootstrap/container.py`.
- Frontend: a layered Next.js App Router app. Route entrypoints live in `frontend/app`, while product code follows `app -> widgets -> features -> entities -> shared` in `frontend/src`.

Use the subsystem docs for the full architecture rules:

- [backend/README.md](backend/README.md)
- [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md)
- [backend/AGENTS.md](backend/AGENTS.md)
- [frontend/README.md](frontend/README.md)
- [frontend/ARCHITECTURE.md](frontend/ARCHITECTURE.md)
- [frontend/AGENTS.md](frontend/AGENTS.md)

## Prerequisites

Install these before working in the repository:

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) for backend environment and dependency management
- Node.js and `npm` for the frontend

## Quick Start

From the repository root:

```bash
make install
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
make dev
```

This starts the local stack with the default ports:

- backend API: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:3000`

Stop all three development processes together with `Ctrl-C`.

## Local Development Workflow

`make dev` starts:

- the backend API server
- the backend worker process
- the frontend development server

The worker is required if you want queued runs to progress beyond `queued`. If you only start the API, run records can still be created, but background execution will not advance.

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
- `make dev`: start backend API, backend worker, and frontend dev server together
- `make lint`: run backend and frontend lint checks
- `make typecheck`: run backend mypy and frontend TypeScript checks
- `make test`: run backend pytest and frontend Vitest suites
- `make build`: run the frontend production build
- `make backend-ci`: run backend CI checks from `backend/Makefile`
- `make frontend-ci`: run frontend CI checks from `frontend/package.json`
- `make ci`: run both backend and frontend CI flows

## Environment Configuration

### Backend

Copy `backend/.env.example` to `backend/.env`.

Key settings:

- `AGENT_ATLAS_API_PREFIX`: API route prefix
- `AGENT_ATLAS_APP_NAME`: application name shown in docs and metadata
- `AGENT_ATLAS_ALLOWED_ORIGINS`: allowed browser origins for local frontend access
- `AGENT_ATLAS_RUNNER_MODE`: execution carrier selection (`auto`, `local`, `docker`, `mock`)
- `AGENT_ATLAS_RUNTIME_MODE`: provider execution behavior (`auto`, `live`, `mock`)
- `AGENT_ATLAS_DATABASE_URL`: SQLite database location for local state
- `AGENT_ATLAS_SEED_DEMO`: whether demo data is seeded on startup
- `AGENT_ATLAS_RUNNER_IMAGE`: Docker image used for docker-based execution
- `AGENT_ATLAS_OPENAI_API_KEY` or `OPENAI_API_KEY`: OpenAI credentials for live mode

### Frontend

Copy `frontend/.env.example` to `frontend/.env.local`.

Key setting:

- `NEXT_PUBLIC_API_BASE_URL`: browser-visible backend base URL, defaulting to `http://127.0.0.1:8000`

## Work By Subproject

Use the root workflow when you want the standard local stack. Drop into a subproject when you need more focused commands.

### Backend

```bash
cd backend
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
cd frontend
npm install
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
npm run ci
```

Additional frontend commands:

- `npm run format`: format frontend files with Prettier
- `npm run format:check`: check formatting without rewriting files
- `npm run lint:fix`: auto-fix lint issues where possible
- `npm run test:coverage`: run Vitest with coverage
- `npm run test:e2e`: run Playwright end-to-end tests against a local frontend server
- `npm run verify`: run lint, typecheck, and coverage tests
- `npm run check`: run format check, lint, and typecheck

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

- backend: `cd backend && make ci`
- frontend: `cd frontend && npm run ci`

## Where To Go Next

- Backend runtime, API surface, and environment details: [backend/README.md](backend/README.md)
- Backend architecture and dependency rules: [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md)
- Frontend setup, testing, and product surfaces: [frontend/README.md](frontend/README.md)
- Frontend architecture rules: [frontend/ARCHITECTURE.md](frontend/ARCHITECTURE.md)
- Repository conventions for contributors and agents: [backend/AGENTS.md](backend/AGENTS.md), [frontend/AGENTS.md](frontend/AGENTS.md)
