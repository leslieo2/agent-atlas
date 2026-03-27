# Agent Atlas Frontend

The frontend is the operator interface for the self-hosted Agent Atlas workbench. It provides the browser UI for browsing runs, inspecting trajectories, launching work, and interacting with backend data exposed by the API.

For the full-stack workflow, start from the repository root README. Use this document when you are working directly on the frontend application.

## What This App Owns

- run dashboard and run-level interaction flows
- trajectory viewing and step inspection
- playground and operator-facing execution surfaces
- client-side data fetching, mapping, and caching for workbench views
- frontend architecture and design system rules for the UI layer

## Architecture

This frontend uses Next.js App Router with a layered product structure:

- `app/`: routes, layouts, metadata, and page entrypoints
- `src/widgets/`: screen and workspace composition
- `src/features/`: focused user capabilities
- `src/entities/`: domain models, mappers, API clients, and entity-scoped query hooks
- `src/shared/`: generic UI primitives and low-level utilities

Dependency direction:

`app -> widgets -> features -> entities -> shared`

Read the full rules in [ARCHITECTURE.md](./ARCHITECTURE.md). Visual and interaction guidance lives in [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md). Contributor and layering guidance lives in [AGENTS.md](./AGENTS.md).

## Local Setup

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`.

By default, the frontend expects the backend at `http://127.0.0.1:8000`.

## Configuration

Copy [`.env.example`](./.env.example) to `.env.local`.

Important setting:

- `NEXT_PUBLIC_API_BASE_URL`: browser-visible backend base URL

If the backend is not running at `http://127.0.0.1:8000`, update `NEXT_PUBLIC_API_BASE_URL` before starting the dev server.

## Implemented Workbench Surfaces

- Run Dashboard: browse, filter, search, and act on run records
- Trajectory Viewer: inspect step graphs and step-level details
- Playground: trigger manual execution flows and inspect outputs

## Developer Commands

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/frontend
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
- `npm run test:unit`
- `npm run test:integration`
- `npm run test:e2e`
- `npm run test:e2e:live`
- `npm run test:e2e:ui`
- `npm run verify`
- `npm run verify:full`
- `npm run check`

## Verification

Typical local verification:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

For the standard frontend CI bundle:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/frontend
npm run ci
```
