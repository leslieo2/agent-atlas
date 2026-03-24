# Repository Guidelines

## Project Structure & Module Organization
This repository is a two-part application:

- `backend/`: FastAPI service (`backend/app`) and backend tests (`backend/tests`).
- `frontend/`: Next.js App Router app (`frontend/app`), reusable UI (`frontend/components`), and client utilities (`frontend/lib`).
- `frontend/test`: Vitest + React Testing Library test files for UI and logic.
- `backend/.venv`, `backend/.uv_cache`, `frontend/node_modules`, and `frontend/.next` are generated and should not be committed.

## Build, Test, and Development Commands
- Backend setup and checks (run in `backend/`):
  - `make install` — create `.venv` and install runtime + dev dependencies via `.[dev]` in `pyproject.toml`.
  - `make fmt` — run Ruff formatter and Python compile check.
  - `make lint` — run Ruff lint/format checks.
  - `make typecheck` — run mypy on `app/`.
  - `make test` — run pytest.
  - `make test-check` — run pytest with coverage checks (`--cov-fail-under=70`).
  - `make security` — run Bandit scan on backend code.
  - `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — start API locally.
- Frontend setup and checks (run in `frontend/`):
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
- Backend tests use `pytest`; put backend tests under `backend/tests` with `test_*.py`.
- Frontend tests use Vitest + React Testing Library; test files are `*.spec.ts`, `*.spec.tsx`, `*.test.ts`, `*.test.tsx` (covered by `frontend/vitest.config.ts`).
- Frontend coverage defaults to `lib/**/*`, `components/**/*`, and `app/**/*`.
- Run at least `make test` and `npm run test` before opening a PR.

## Commit & Pull Request Guidelines
The root and both subdirectories currently have no git history on `master`, so there is no local convention to infer. Use Conventional Commits now (`feat:`, `fix:`, `refactor:`, `test:`).
- PRs should include what changed, why, related issue/task link, and command outputs (`make test`, `npm run test`, `make lint` / `npm run lint`, `make typecheck` / `npm run typecheck`).
- For UI work, include relevant screenshots or short screen recordings.
- For API changes, include example request/response payloads and affected endpoints.

## Security & Configuration Tips
- Copy `backend/.env.example` to `backend/.env` and configure environment values before running.
- Set `NEXT_PUBLIC_API_BASE_URL` in frontend when backend URL is not `http://127.0.0.1:8000`.
- Do not commit secrets, local database dumps, or generated artifacts.
