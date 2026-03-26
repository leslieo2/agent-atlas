# Agent Atlas

Agent Atlas is a monorepo containing a FastAPI backend and a Next.js frontend.

## Repository Structure

- `backend/`: FastAPI service, feature modules, backend tests, and backend-specific tooling.
- `frontend/`: Next.js App Router application, layered frontend source code, and frontend tests.
- `Makefile`: Root-level entrypoint for common cross-project commands.

## Prerequisites

- Python with `uv` installed for backend workflows
- Node.js and `npm` for frontend workflows

## Root Commands

Run these from the repository root:

```bash
make help
make install
make dev
make lint
make typecheck
make test
make build
make backend-ci
make frontend-ci
make ci
```

What they do:

- `make install`: install backend and frontend dependencies
- `make dev`: start the backend API, backend worker, and frontend dev server together
- `make lint`: run backend lint checks and frontend lint checks
- `make typecheck`: run backend mypy and frontend TypeScript checks
- `make test`: run backend pytest and frontend Vitest
- `make build`: run the frontend production build
- `make backend-ci`: run backend CI checks from `backend/Makefile`
- `make frontend-ci`: run frontend CI checks from `frontend/package.json`
- `make ci`: run both backend and frontend CI checks

## Working By Subproject

Use subproject-local commands when you need more targeted workflows.

For the standard local stack, use `make dev` from the repository root. It starts:

- backend API on `http://127.0.0.1:8000`
- backend worker
- frontend dev server on `http://127.0.0.1:3000`

Press `Ctrl-C` to stop all three processes together.

### Backend

```bash
cd backend
make install
make run-api
make ci
```

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run ci
```

## Development Notes

- Backend conventions and architecture rules live in [`backend/AGENTS.md`](backend/AGENTS.md).
- Frontend conventions and layering rules live in [`frontend/AGENTS.md`](frontend/AGENTS.md) and [`frontend/ARCHITECTURE.md`](frontend/ARCHITECTURE.md).
- Backend environment variables should be configured from `backend/.env.example`.
- Set `NEXT_PUBLIC_API_BASE_URL` in frontend when the backend is not running on `http://127.0.0.1:8000`.
