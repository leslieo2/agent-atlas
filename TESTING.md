# Agent Atlas Testing Strategy

This repository uses a layered testing model aligned to the current governed-asset control-plane
shape described in [prd.md](/Users/leslie/PycharmProjects/agent-atlas/prd.md).

## Test Pyramid

- `unit`
  - Goal: verify pure business rules, intake and validation helpers, manifest/runtime metadata
    normalization, execution/runtime loading, exporter formatting, and frontend API/data mapping.
  - Scope: no real network, no browser navigation, no background process orchestration beyond local stubs and mocks.
- `integration`
  - Goal: verify boundary collaboration inside one app.
  - Backend: FastAPI routes for governed asset listing, transitional bootstrap intake, validation-run
    creation, experiment/run creation, persistence, and export flow.
  - Frontend: rendered React components plus mocked API boundaries.
- `e2e`
  - Goal: verify the main governed-asset intake -> run -> evidence -> export workflow through the
    actual UI or full backend workflow.
  - Frontend: Playwright against a running Next.js app with route interception or live services.
  - Backend: end-to-end flows across governed asset intake, runnable catalog, run creation,
    evidence inspection, and export.

## PRD-to-Suite Mapping

- Govern runnable agent assets
  - Backend unit: manifest parsing, duplicate detection, intake helpers, and validation metadata
    normalization
  - Backend integration: `GET /api/v1/agents/published`, `POST /api/v1/agents/bootstrap/claude-code`,
    `POST /api/v1/agents/{agent_id}/validation-runs`
  - Frontend integration: Agents workspace rendering, governed asset grouping, transitional bootstrap
    bridge, validation actions, and experiment handoff links
- Run an agent
  - Backend integration: experiment/run creation, trajectory persistence, structured runtime errors,
    and invalid published-asset rejection
  - Frontend integration: `ExperimentsWorkspace`, run/evidence summary surfaces
  - Frontend e2e: create or intake a governed asset, then create an experiment/run from the selected
    published asset
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

- Replay for governed assets
- Eval for governed assets
- LangChain plugin support
- MCP plugin support
- Deterministic tool-step replay
- External package or remote plugin sources
- Versioned publish snapshots

They may retain historical tests where needed, but they do not define the primary product verification path.

## Backend Commands

- Full suite: `cd apps/control-plane && make test`
- Unit only: `cd apps/control-plane && make test-unit`
- Integration only: `cd apps/control-plane && make test-integration`
- E2E only: `cd apps/control-plane && make test-e2e`
- TDD fast loop for unit work: `cd apps/control-plane && make test-tdd-unit`
- TDD fast loop for integration work: `cd apps/control-plane && make test-tdd-integration`

`apps/control-plane/tests/conftest.py` auto-labels tests by directory:

- `tests/unit/**` => `@pytest.mark.unit`
- `tests/integration/**` => `@pytest.mark.integration`
- `tests/e2e/**` => `@pytest.mark.e2e`

Files kept at the test root are also classified:

- `test_services.py` => `unit`
- `test_runs_api.py`, `test_health.py` => `integration`

## Frontend Commands

- Full Vitest suite: `cd apps/web && npm run test`
- Unit only: `cd apps/web && npm run test:unit`
- Integration only: `cd apps/web && npm run test:integration`
- E2E only: `cd apps/web && npm run test:e2e`
- Interactive e2e debugging: `cd apps/web && npm run test:e2e:ui`
- TDD loop for component and utility work: `cd apps/web && npm run test:tdd`
- TDD loop for isolated unit work: `cd apps/web && npm run test:tdd:unit`
- TDD loop for component integration work: `cd apps/web && npm run test:tdd:integration`
- Hermetic frontend CI gate: `cd apps/web && npm run ci`
- Full local verification gate: `cd apps/web && npm run verify:full`

`apps/web/test/setup.ts` provides stable browser shims for `matchMedia`, `ResizeObserver`, and `IntersectionObserver`, which avoids false failures in jsdom-based integration tests.

`apps/web/e2e/support/mockApi.ts` centralizes Playwright API fixtures so new governed-asset intake,
validation, and run flows can be added without repeating raw `page.route` boilerplate.

## TDD Workflow

Use a strict red-green-refactor loop:

1. Write or update one failing test closest to the behavior you are changing.
2. Run the narrowest command possible.
3. Implement the minimal code to pass.
4. Refactor with the same narrow test command still green.
5. Before merging, run the broader layer and then the full verification gate.

Recommended command path:

1. Agent intake or backend service change: `make test-tdd-unit`
2. Backend API contract or persistence change: `make test-tdd-integration`
3. Frontend mapping or util change: `npm run test:tdd:unit`
4. Frontend component behavior change: `npm run test:tdd:integration`
5. Cross-screen governed-asset intake, validation, or run workflow change: `npm run test:e2e:ui`

## Coverage Guidance

- Keep unit tests dominant in count and speed.
- Use integration tests to cover intake/validation flows, route wiring, schema contracts, and state
  transitions.
- Reserve e2e for a few golden paths from the current PRD.
- Do not push low-level mapping checks into Playwright.
- Do not use e2e to compensate for missing unit tests.
