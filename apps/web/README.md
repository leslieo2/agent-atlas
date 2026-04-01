# Agent Atlas Frontend

The frontend is the operator interface for Agent Atlas. It provides the browser UI for control-plane
orchestration and evidence-plane workflows around agents, datasets, experiments, and exports.

The frontend is intentionally a control-plane UI, not a direct vendor console for tracing or
experimentation. When external observability backends such as Phoenix are integrated, the frontend
should continue to consume Atlas-owned APIs, summaries, and deep links instead of binding directly
to vendor SDKs.

For the full-stack workflow, start from the repository root README. Use this document when you are
working directly on the frontend application.

## What This App Owns

- Agents workspace and publication-oriented interaction flows
- datasets and eval workspaces
- export-oriented interaction flows
- client-side data fetching, mapping, and caching for control-plane views
- frontend architecture and design system rules for the UI layer
- evidence summaries and deep links that stay attached to Atlas-owned records

Supporting, but not long-term primary, surfaces:

- run-level drill-downs under eval workflows
- trajectory summaries and Phoenix links for debugging
- no separate legacy workbench routes; Atlas now centers the four primary workspaces

## Architecture

This frontend uses Next.js App Router with a layered product structure:

- `app/`: routes, layouts, metadata, and page entrypoints
- `src/widgets/`: screen and workspace composition
- `src/features/`: focused user capabilities
- `src/entities/`: domain models, mappers, API clients, and entity-scoped query hooks
- `src/shared/`: generic UI primitives and low-level utilities

Dependency direction:

`app -> widgets -> features -> entities -> shared`

Read the full rules in [ARCHITECTURE.md](./ARCHITECTURE.md). Visual and interaction guidance lives
in [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md). Contributor and layering guidance lives in
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

## Implemented Workbench Surfaces

- Agents: review agent definitions, seal Atlas snapshots, and inspect provenance plus execution references
- Datasets: upload and manage sample sets
- Experiments: create batch runs and inspect result summaries and failures
- Export actions: download offline artifacts from run and eval workflows

Legacy surfaces still present in the codebase but being downscoped:

- Runs
- Trajectory Viewer
- Playground

## Product Direction

The frontend should evolve in a way that reinforces Atlas as the control plane:

- center the IA on `Agents`, `Datasets`, `Experiments`, and `Exports`
- show publication, compatibility, execution-profile, and provenance state inside Atlas-owned records
- keep tracing UI limited to evidence summaries, reference fields, evidence association, and Phoenix deep links
- avoid rebuilding a complete observability product inside the frontend
- avoid growing manual-run or playground surfaces as first-class product workflows
- preserve explicit snake_case-to-camelCase payload mapping when backend contracts expand

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
