# Repository Guidelines

## Project Structure & Module Organization
This repository is organized as a monorepo with product-facing apps at the top level:

- `apps/control-plane/`: FastAPI service (`apps/control-plane/app`) and backend tests (`apps/control-plane/tests`).
  Control-plane architecture is feature-module based under `apps/control-plane/app/modules`; see `apps/control-plane/AGENTS.md` for backend-specific layering and dependency rules.
- `apps/web/`: Next.js App Router app with thin route entrypoints in `apps/web/app` and layered product code in `apps/web/src`.
  Frontend architecture follows `app -> widgets -> features -> entities -> shared`; see `apps/web/ARCHITECTURE.md` and `apps/web/AGENTS.md` for the current layering and ownership rules.
- `packages/`: shared contracts and SDK scaffolds for cross-plane reuse.
- `runtimes/`: runner scaffolds for framework-specific execution adapters.
- `docs/`, `infra/`, and `schemas/`: architecture docs, deployment assets, and neutral schema definitions.
- `apps/web/test`: Vitest + React Testing Library test files for UI and logic.
- `apps/control-plane/.venv`, `apps/control-plane/.uv_cache`, `apps/web/node_modules`, and `apps/web/.next` are generated and should not be committed.

## Build, Test, and Development Commands
- Control-plane setup and checks (run in `apps/control-plane/`):
  - `make install` — create `.venv` and install runtime + dev dependencies via `.[dev]` in `pyproject.toml`.
  - `make fmt` — run Ruff formatter and Python compile check.
  - `make lint` — run Ruff lint/format checks.
  - `make typecheck` — run mypy on `app/`.
  - `make test` — run pytest.
  - `make test-check` — run pytest with coverage checks (`--cov-fail-under=70`).
  - `make security` — run Bandit scan on backend code.
  - `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — start API locally.
- Web app setup and checks (run in `apps/web/`):
  - `npm install` — install JS dependencies.
  - `npm run dev` — run Next.js dev server on `http://localhost:3000`.
  - `npm run lint` — run ESLint.
  - `npm run typecheck` — run TypeScript strict check (`tsc --noEmit`).
  - `npm run test` — run Vitest suite.
  - `npm run build` — production build.
  - `npm run ci` — run lint + typecheck + test + build.

## Coding Style & Naming Conventions
- Python: 4-space indentation, LF line endings, quote-style double, line length 100 (`ruff` config).
- TypeScript/React: 2-space indentation, strict TypeScript enabled, Prettier + ESLint formatting.
- Naming: Python uses `snake_case` for functions/modules/variables, `PascalCase` for classes; frontend uses `camelCase` for hooks/functions and `PascalCase` for React components/files.
- Keep API payload mapping explicit and deterministic; avoid implicit schema guessing.

## Testing Guidelines
- Backend tests use `pytest`; put backend tests under `apps/control-plane/tests` with `test_*.py`.
- Frontend tests use Vitest + React Testing Library; test files are `*.spec.ts`, `*.spec.tsx`, `*.test.ts`, `*.test.tsx` (covered by `apps/web/vitest.config.ts`).
- Frontend coverage defaults to `app/**/*` and `src/**/*`.
- Run at least `make test` and `npm run test` before opening a PR.

## Commit & Pull Request Guidelines
The root and both subdirectories currently have no git history on `master`, so there is no local convention to infer. Use Conventional Commits now (`feat:`, `fix:`, `refactor:`, `test:`).
- PRs should include what changed, why, related issue/task link, and command outputs (`make test`, `npm run test`, `make lint` / `npm run lint`, `make typecheck` / `npm run typecheck`).
- For UI work, include relevant screenshots or short screen recordings.
- For API changes, include example request/response payloads and affected endpoints.

## Security & Configuration Tips
- Copy `apps/control-plane/.env.example` to `apps/control-plane/.env` and configure environment values before running.
- Set `NEXT_PUBLIC_API_BASE_URL` in frontend when backend URL is not `http://127.0.0.1:8000`.
- Do not commit secrets, local database dumps, or generated artifacts.
