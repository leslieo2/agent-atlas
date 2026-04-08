# Repository Guidelines

## Project Structure & Module Organization
This is a Next.js App Router frontend in TypeScript.

- `app/`: routes and global UI shell.
  - `app/page.tsx`: main entry route.
  - `app/layout.tsx`: shared layout/metadata.
  - `app/globals.css`: global styles.
- `src/widgets/`: page or workspace composition. Widgets orchestrate features and entity queries for a screen.
- `src/features/`: focused user capabilities such as filters, run actions, replay editors, and result tables.
- `src/entities/`: domain models, API clients, and explicit payload mappers.
- `src/shared/`: shared UI primitives, HTTP utilities, and server-state helpers such as the React Query provider and hooks.
- `test/`: test setup and feature tests.
- `.next/`, `node_modules/`: generated/artifact folders; do not edit.
- `public/`: create if new static assets are needed.

## Build, Test, and Development Commands
- `npm install`: install dependencies.
- `make install-ci`: install dependencies with `npm ci` for reproducible CI runs.
- `npm run dev`: start local dev server at `http://localhost:3000`.
- `npm run lint`: run ESLint.
- `npm run typecheck`: run TypeScript strict checks (`tsc --noEmit`).
- `npm run format:check`: verify formatting.
- `npm run format`: format all supported files.
- `npm run test`: run Vitest suite.
- `npm run test:watch`: watch mode for rapid iteration.
- `npm run build`: production build.
- `make ci`: hermetic frontend CI bundle (`lint + typecheck + coverage + build`).
- `npm run check` / `npm run verify`: grouped checks for daily work.
- `npm run verify:full`: local full verification bundle (`npm run ci` + Playwright e2e).

## Coding Style & Naming Conventions
- Tooling: ESLint + Prettier.
- `.prettierrc.json`: 2-space indent, semicolons, double quotes, no trailing commas, print width 120.
- Use strict TypeScript types (`strict: true`).
- `PascalCase` for React component files/names.
- `camelCase` for variables/functions/hooks.
- API payload mapping should keep conversion explicit (snake_case API -> camelCase app models).
- Keep route files thin and delegate screen orchestration to `src/widgets/`.
- Use path alias imports via `@/` where convenient.

## Testing Guidelines
- Framework: Vitest + React Testing Library.
- Test files: `*.spec.ts`, `*.spec.tsx`, `*.test.ts`, `*.test.tsx`.
- Setup file: `test/setup.ts`.
- Current tests include examples in `test/fixtures.spec.ts`.
- Coverage scope in config: `app/**/*`, `src/**/*`.
- Run coverage manually with `npx vitest run --coverage` when needed.

## Commit & Pull Request Guidelines
- Current git history is empty (`master` has no commits yet), so no local convention can be extracted yet.
- Use [Conventional Commits](https://www.conventionalcommits.org/) until a team convention is documented (for example: `feat: add trajectory step filter`).
- PRs should include:
  - summary of behavior changes,
  - linked issue/task,
  - validation commands run,
  - screenshots for UI changes,
  - any API/environment changes (`NEXT_PUBLIC_API_BASE_URL`, backend endpoint changes, etc.).

## Security & Configuration Notes
- Backend base URL is read from `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://127.0.0.1:8000`).
- Do not commit secrets or real API keys in source files.
