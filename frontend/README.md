# Agent Flight Recorder Frontend

This is a Next.js + TypeScript frontend scaffold for the PRD v1 workbench.

## Start

```bash
cd /Users/leslie/PycharmProjects/agent-flight-recorder/frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

If the backend is not running on `http://127.0.0.1:8000`, copy `frontend/.env.example` to `frontend/.env.local` and set `NEXT_PUBLIC_API_BASE_URL`.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the frontend layering rules, dependency direction, and module ownership. The current frontend is organized as thin route entrypoints in `app/` plus layered product code in `src/widgets`, `src/features`, `src/entities`, and `src/shared`, with TanStack Query handling server-state coordination.

## Design Language

See [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) for the frontend visual system, page composition rules, tone, tokens, and component guidance. Use it together with `ARCHITECTURE.md`: architecture decides where UI code belongs, design language decides how it should feel and read.

## 质量检查命令

```bash
npm run format:check   # 格式检查
npm run lint           # ESLint
npm run typecheck      # TypeScript 类型检查
npm run test           # Vitest 测试
npm run build          # 生产编译
npm run ci             # lint + typecheck + test + build
```

```bash
npm run format         # 一键格式化
npm run lint:fix       # 自动修复 ESLint 问题
npm run check          # format:check + lint + typecheck
npm run verify         # lint + typecheck + test
```

## Implemented v1 workbench surfaces

- Run Dashboard: filter/search run records, execute actions, and export placeholders.
- Trajectory Viewer: step graph with React Flow and step detail list.
- Playground: manual execution entrypoint with runtime outputs.

## PRD mapping

This project scaffolds the workflow loop from the PRD:
run → observe trajectory → export artifacts.
