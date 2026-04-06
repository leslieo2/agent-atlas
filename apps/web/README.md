# Agent Atlas Frontend

The frontend is the operator-facing UI for Agent Atlas. It renders the product contract already
defined in the root README:

`governed asset -> execution profile -> run -> evidence -> export`

Use this document for local frontend ownership, setup, and verification. For the public product
story, start from the repository root README instead of treating this file as a second authority.

## What This App Owns

- the `Agents`, `Datasets`, `Experiments`, and `Exports` workspaces
- client-side data fetching, mapping, and caching for Atlas-owned APIs
- evidence summaries and deep links attached to Atlas-owned records
- frontend architecture, design system, and contributor rules for the web app

Supporting views, not first-class product centers:

- run-level drill-downs under experiment workflows
- Phoenix deep links and evidence summaries for debugging
- execution-profile, provenance, and runner detail shown as secondary metadata

## Product Framing Rules

The frontend should reinforce Atlas as the control plane:

- keep the IA centered on `Agents / Datasets / Experiments / Exports`
- keep the product chain legible as `governed asset -> execution profile -> run -> evidence -> export`
- keep execution detail behind execution-profile, provenance, or evidence summaries instead of
  elevating it into first-class navigation or object nouns
- keep Phoenix deeplink-only inside the product UI; do not grow a peer tracing workspace
- treat validation as lifecycle and evidence state on governed assets and runs, not as a separate
  product center
- preserve explicit snake_case-to-camelCase mapping at entity boundaries when backend contracts
  expand

## Architecture

This frontend uses Next.js App Router with a layered structure:

- `app/`: routes, layouts, metadata, and page entrypoints
- `src/widgets/`: screen and workspace composition
- `src/features/`: focused user capabilities
- `src/entities/`: domain models, mappers, API clients, and entity-scoped query hooks
- `src/shared/`: generic UI primitives and low-level utilities

Dependency direction:

`app -> widgets -> features -> entities -> shared`

Read the full layering rules in [ARCHITECTURE.md](./ARCHITECTURE.md). Visual and interaction
guidance lives in [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md). Contributor guidance lives in
[AGENTS.md](./AGENTS.md).

## Local Setup

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/web
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

If the backend is not running at `http://127.0.0.1:8000`, update `NEXT_PUBLIC_API_BASE_URL` before
starting the dev server.

The frontend has no `runtime_mode` switch. Runtime execution behavior is configured on the backend
through canonical control-plane settings and explicit run execution configuration.

## Implemented Workspaces

- Agents: intake, govern, and validate runnable assets
- Datasets: upload and manage sample sets
- Experiments: create batch runs, compare outcomes, and inspect evidence summaries
- Exports: create and download offline handoff artifacts

## Developer Commands

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/web
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
- `npm run test:unit`
- `npm run test:integration`
- `npm run test:e2e`
- `npm run test:e2e:live`
- `npm run test:e2e:ui`
- `npm run verify`
- `npm run verify:ci`
- `npm run verify:full`
- `npm run check`

## Verification

Typical local verification:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/web
npm run lint
npm run typecheck
npm run test
npm run build
```

For the standard frontend CI bundle:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/web
npm run ci
```

For the full local verification bundle, including browser smoke coverage against a local backend:

```bash
cd /Users/leslie/PycharmProjects/agent-atlas/apps/web
npm run verify:full
```
