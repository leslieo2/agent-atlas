# Agent Flight Recorder Testing Strategy

This repository now uses a layered testing model derived from the product flows in [prd.md](/Users/leslie/PycharmProjects/agent-flight-recorder/prd.md).

## Test pyramid

- `unit`
  - Goal: verify pure business rules, schema mapping, adapter normalization, exporter formatting, and frontend API/data mapping.
  - Scope: no real network, no browser navigation, no background process orchestration beyond local stubs/mocks.
- `integration`
  - Goal: verify boundary collaboration inside one app.
  - Backend: FastAPI routes + services + in-memory state.
  - Frontend: rendered React components + mocked API module / fetch boundary.
- `e2e`
  - Goal: verify PRD user flows through the actual UI or full backend workflow.
  - Frontend: Playwright against a running Next.js app with route interception.
  - Backend: end-to-end API flows across dataset, run, trajectory, replay, eval, and export.

## PRD-to-suite mapping

- Run an agent
  - Backend integration: `POST /runs`, `GET /runs/{id}`, trajectory persistence
  - Frontend integration: `Playground`, `RunDashboard`
  - Frontend e2e: dashboard create-run flow
- Debug a run
  - Backend integration: traces ingest + normalize contracts
  - Frontend integration: `TrajectoryViewer`
  - Frontend e2e: trajectory diff flow
- Replay a step
  - Backend unit: replay diff generation
  - Backend e2e: replay API inside full workbench flow
  - Frontend integration: `StepReplayPanel`
- Evaluate a dataset
  - Backend unit: eval scoring and job transitions
  - Backend e2e: dataset + eval job lifecycle
  - Frontend integration: `EvalBench`
- Export training artifacts
  - Backend unit: JSONL / Parquet exporter serialization
  - Backend e2e: export endpoint and artifact download
  - Frontend e2e: export trigger from dashboard

## Backend commands

- Full suite: `cd backend && make test`
- Unit only: `cd backend && make test-unit`
- Integration only: `cd backend && make test-integration`
- E2E only: `cd backend && make test-e2e`
- TDD fast loop for unit work: `cd backend && make test-tdd-unit`
- TDD fast loop for integration work: `cd backend && make test-tdd-integration`

`backend/tests/conftest.py` auto-labels tests by directory:

- `tests/unit/**` => `@pytest.mark.unit`
- `tests/integration/**` => `@pytest.mark.integration`
- `tests/e2e/**` => `@pytest.mark.e2e`

Files kept at the test root are also classified:

- `test_services.py` => `unit`
- `test_runs_api.py`, `test_health.py` => `integration`

## Frontend commands

- Full Vitest suite: `cd frontend && npm run test`
- Unit only: `cd frontend && npm run test:unit`
- Integration only: `cd frontend && npm run test:integration`
- E2E only: `cd frontend && npm run test:e2e`
- Interactive e2e debugging: `cd frontend && npm run test:e2e:ui`
- TDD loop for component/lib work: `cd frontend && npm run test:tdd`
- TDD loop for isolated unit work: `cd frontend && npm run test:tdd:unit`
- TDD loop for component integration work: `cd frontend && npm run test:tdd:integration`
- Full verification gate: `cd frontend && npm run verify:full`

`frontend/test/setup.ts` provides stable browser shims for `matchMedia`, `ResizeObserver`, and `IntersectionObserver`, which avoids false failures in jsdom-based integration tests.

`frontend/e2e/support/mockApi.ts` centralizes Playwright API fixtures so new PRD flows can be added without repeating raw `page.route` boilerplate.

## TDD workflow

Use a strict red-green-refactor loop:

1. Write or update one failing test closest to the behavior you are changing.
2. Run the narrowest command possible.
3. Implement the minimal code to pass.
4. Refactor with the same narrow test command still green.
5. Before merging, run the broader layer and then the full verification gate.

Recommended command path:

1. Pure backend service change: `make test-tdd-unit`
2. Backend API contract change: `make test-tdd-integration`
3. Frontend mapping/util change: `npm run test:tdd:unit`
4. Frontend component behavior change: `npm run test:tdd:integration`
5. Cross-screen user flow change: `npm run test:e2e:ui`

## Coverage guidance

- Keep unit tests dominant in count and speed.
- Use integration tests to cover route wiring, schema contracts, and state transitions.
- Reserve e2e for a few golden paths from the PRD.
- Do not push low-level mapping checks into Playwright.
- Do not use e2e to compensate for missing unit tests.
