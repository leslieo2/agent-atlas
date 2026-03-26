# Agent Flight Recorder Testing Strategy

This repository uses a layered testing model aligned to the current registered-agent product shape described in [prd.md](/Users/leslie/PycharmProjects/agent-flight-recorder/prd.md).

## Test Pyramid

- `unit`
  - Goal: verify pure business rules, registry loading, schema mapping, runtime loading, exporter formatting, and frontend API/data mapping.
  - Scope: no real network, no browser navigation, no background process orchestration beyond local stubs and mocks.
- `integration`
  - Goal: verify boundary collaboration inside one app.
  - Backend: FastAPI routes, registered-agent catalog, run creation, persistence, export flow.
  - Frontend: rendered React components plus mocked API boundaries.
- `e2e`
  - Goal: verify the main registered-agent user workflow through the actual UI or full backend workflow.
  - Frontend: Playwright against a running Next.js app with route interception or live services.
  - Backend: end-to-end flows across agent catalog, run creation, trajectory inspection, and export.

## PRD-to-Suite Mapping

- Registered agent catalog
  - Backend unit: registry parsing and entrypoint validation
  - Backend integration: `GET /agents`
  - Frontend integration: Playground agent selector and agent metadata rendering
- Run an agent
  - Backend integration: `POST /runs`, `GET /runs/{id}`, trajectory persistence, structured runtime errors
  - Frontend integration: `Playground`, `RunDashboard`
  - Frontend e2e: Playground create-run flow from selected `agent_id`
- Debug a run
  - Backend integration: trajectory and trace persistence contracts
  - Frontend integration: `TrajectoryViewer`, step inspection surfaces
  - Frontend e2e: open run workspace and inspect recorded execution data
- Export training artifacts
  - Backend unit: JSONL exporter serialization
  - Backend integration: export endpoint and artifact download
  - Frontend e2e: export trigger from dashboard or run workspace

## Out of Current v1 Test Scope

The following are intentionally not part of the current v1 golden-path test matrix:

- Replay for registered agents
- Eval for registered agents
- LangChain registered-agent support
- MCP registered-agent support
- Deterministic tool-step replay

They may retain historical tests where needed, but they do not define the primary product verification path.

## Backend Commands

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

## Frontend Commands

- Full Vitest suite: `cd frontend && npm run test`
- Unit only: `cd frontend && npm run test:unit`
- Integration only: `cd frontend && npm run test:integration`
- E2E only: `cd frontend && npm run test:e2e`
- Interactive e2e debugging: `cd frontend && npm run test:e2e:ui`
- TDD loop for component and utility work: `cd frontend && npm run test:tdd`
- TDD loop for isolated unit work: `cd frontend && npm run test:tdd:unit`
- TDD loop for component integration work: `cd frontend && npm run test:tdd:integration`
- Full verification gate: `cd frontend && npm run verify:full`

`frontend/test/setup.ts` provides stable browser shims for `matchMedia`, `ResizeObserver`, and `IntersectionObserver`, which avoids false failures in jsdom-based integration tests.

`frontend/e2e/support/mockApi.ts` centralizes Playwright API fixtures so new registered-agent flows can be added without repeating raw `page.route` boilerplate.

## TDD Workflow

Use a strict red-green-refactor loop:

1. Write or update one failing test closest to the behavior you are changing.
2. Run the narrowest command possible.
3. Implement the minimal code to pass.
4. Refactor with the same narrow test command still green.
5. Before merging, run the broader layer and then the full verification gate.

Recommended command path:

1. Registry or backend service change: `make test-tdd-unit`
2. Backend API contract or persistence change: `make test-tdd-integration`
3. Frontend mapping or util change: `npm run test:tdd:unit`
4. Frontend component behavior change: `npm run test:tdd:integration`
5. Cross-screen registered-agent workflow change: `npm run test:e2e:ui`

## Coverage Guidance

- Keep unit tests dominant in count and speed.
- Use integration tests to cover registry loading, route wiring, schema contracts, and state transitions.
- Reserve e2e for a few golden paths from the current PRD.
- Do not push low-level mapping checks into Playwright.
- Do not use e2e to compensate for missing unit tests.
