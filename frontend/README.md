# Agent Flight Recorder Frontend

This is a Next.js + TypeScript frontend scaffold for the PRD v1 workbench.

## Start

```bash
cd /Users/leslie/PycharmProjects/agent-flight-recorder/frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the frontend layering rules, dependency direction, and module ownership.

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
- Step Replay: editable prompt/model/tool payload with Monaco diff.
- Eval Bench: dataset-aware evaluation metrics and failure drill-down.
- Playground: manual execution entrypoint with runtime outputs.

## PRD mapping

This project scaffolds the workflow loop from the PRD:
run → observe trajectory → replay step → evaluate dataset → export artifacts (UI placeholder).
