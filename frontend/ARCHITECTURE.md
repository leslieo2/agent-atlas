# Frontend Architecture

This frontend uses a lightweight layered architecture on top of Next.js App Router. The goal is to keep route entrypoints thin, keep domain data mapping explicit, and stop dependencies from drifting upward.

## Dependency Direction

Imports must flow in one direction:

`app -> widgets -> features -> entities -> shared`

Allowed responsibilities:

- `app/`: routing, layout, metadata, URL params, and page entrypoints.
- `src/widgets/`: page or workspace composition. A widget can orchestrate multiple features and entities.
- `src/features/`: a focused user capability such as filtering runs, launching a replay, or rendering a results table.
- `src/entities/`: domain models, API clients, mappers, entity-scoped query hooks, and entity-level presentation helpers.
- `src/shared/`: low-level UI primitives and generic utilities with no product workflow knowledge.

## Current Conventions

- Route files should stay thin and delegate immediately to a widget.
- API payload normalization belongs in `src/entities/*/mapper.ts`.
- Entity API clients and entity-scoped query hooks belong in `src/entities/*/`.
- `src/shared/query/` owns only generic React Query client/provider setup, not entity-aware fetch hooks.
- Fetching and multi-step screen orchestration belongs in widgets or widget-local model hooks.
- Reusable entity display helpers should live with the entity, not inside a widget.
- Test fixtures belong under `test/`, not in app-facing code directories.

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
- Do not introduce a separate global client store unless state starts crossing multiple workspaces in ways React Query cannot model cleanly.
