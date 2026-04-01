# Frontend Architecture

This frontend uses a lightweight layered architecture on top of Next.js App Router. The goal is to keep route entrypoints thin, keep domain data mapping explicit, and stop dependencies from drifting upward.

## Dependency Direction

Imports must flow in one direction:

`app -> widgets -> features -> entities -> shared`

Allowed responsibilities:

- `app/`: routing, layout, metadata, URL params, and page entrypoints.
- `src/widgets/`: page or workspace composition. A widget can orchestrate multiple features and entities.
- `src/features/`: a focused user capability such as filtering evidence rows or rendering a results table.
- `src/entities/`: domain models, API clients, mappers, entity-scoped query hooks, and entity-level presentation helpers.
- `src/shared/`: low-level UI primitives and generic utilities with no product workflow knowledge.

External backend rule:

- observability or evaluation vendors such as Phoenix stay behind backend-owned APIs, summaries, and deep links
- frontend entities should not call vendor APIs directly
- first-class Atlas workspaces should converge on `Agents`, `Datasets`, `Experiments`, and `Exports`
- run details, tracing deep links, and other evidence drill-downs are supporting views, not the target product center

## Current Conventions

- Route files should stay thin and delegate immediately to a widget.
- API payload normalization belongs in `src/entities/*/mapper.ts`.
- Entity API clients and entity-scoped query hooks belong in `src/entities/*/`.
- `src/shared/query/` owns only generic React Query client/provider setup, not entity-aware fetch hooks.
- Fetching and multi-step screen orchestration belongs in widgets or widget-local model hooks.
- Reusable entity display helpers should live with the entity, not inside a widget.
- Test fixtures belong under `test/`, not in app-facing code directories.
- Visual and interaction rules belong in `DESIGN_LANGUAGE.md`, not in this architecture doc.

## Guardrails

- `features` must not import from `widgets`.
- `entities` must not import from `features` or `widgets`.
- `shared` must not import from higher layers.
- When widget state becomes large, split it into `ui.tsx` and `model.ts` or `useXxx.ts` inside the widget folder rather than inventing a new global state layer.
- These rules are enforced by `test/architecture.spec.ts`.

## Current Decisions

- Keep App Router as the routing layer.
- Keep page-level orchestration local to widgets.
- Use TanStack Query for server state, cache keys, mutations, and invalidation across workspaces.
- Keep the backend as the integration boundary for external observability and eval systems.
- Prefer Phoenix deep links over rebuilding trace, prompt, evaluator, or experiment tooling in the
  frontend.
- Treat legacy runtime-host surfaces such as standalone runs or playground flows as transitional
  residue, not as the long-term information architecture.
- Do not introduce a separate global client store unless state starts crossing multiple workspaces in ways React Query cannot model cleanly.
