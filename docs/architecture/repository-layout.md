# Repository Layout

Agent Atlas uses a monorepo organized by platform plane.

The repository should be read with one rule in mind:

- the top level is split into product-facing apps, runtimes, shared packages, infra, and schemas
- the repository as a whole is not one giant hexagonal application
- only the control plane defaults to a heavier ports-and-adapters structure internally

This matches the current stage of the product. Contracts such as `RunSpec`, runtime events, and
export metadata still change across the UI, control plane, workers, and runners, so keeping those
surfaces in one repository reduces coordination friction.

## Top-Level Layout

The current repository layout is:

```text
agent-atlas/
├─ apps/
│  ├─ web/                         # Next.js operator UI
│  ├─ control-plane/               # FastAPI control plane and worker
│  ├─ executor-gateway/            # execution entrypoint and scheduler adapters
│  ├─ data-plane-api/              # data-plane read/write API
│  ├─ data-ingestion/              # event and trace normalization pipeline
│  ├─ eval-worker/                 # evaluator / batch scoring worker
│  └─ export-worker/               # offline export and manifest generation worker
├─ runtimes/
│  ├─ runner-base/
│  ├─ runner-langgraph/
│  ├─ runner-openai-agents/
│  ├─ runner-inspect/
│  └─ runner-custom/
├─ packages/
│  ├─ contracts/
│  │  └─ python/                   # current shared contracts package
│  ├─ config/
│  ├─ runtime-sdk/                 # runtime bootstrap and neutral observability helpers
│  ├─ tool-gateway-sdk/
│  ├─ model-gateway-sdk/
│  └─ testkit/
├─ infra/
│  ├─ k8s/
│  ├─ terraform/
│  ├─ docker/
│  ├─ compose/
│  └─ observability/               # OTLP collector and vendor-specific observability backends
├─ schemas/
│  ├─ jsonschema/
│  ├─ openapi/
│  └─ protobuf/
├─ docs/
├─ scripts/
└─ .github/
```

Interpret the top level as follows:

- `apps/` contains product-facing services and platform workers.
- `runtimes/` contains execution-side adapters that consume shared contracts and run agents in a
  specific framework or carrier.
- `packages/` contains cross-plane shared libraries.
- `infra/` contains deployment, local compose, container, and observability assets.
- `schemas/` is the neutral source-of-truth area for platform contracts that should not become
  control-plane internals.

For the runtime-to-observability boundary specifically:

- runtime-owned code should emit telemetry through neutral OTLP configuration, not through a
  Phoenix-specific runtime contract
- `packages/runtime-sdk/` is the landing zone for shared runtime bootstrap and OTLP-side helpers
- `infra/observability/` is where collector and backend wiring belongs
- Phoenix remains a tooling backend for trace inspection and links, not the canonical runtime
  contract

## What Uses Hexagonal Design

Hexagonal design applies primarily to the control plane because that is where Atlas-owned business
semantics live.

Current control-plane layout:

```text
apps/control-plane/
├─ app/
│  ├─ api/                         # thin route re-exports
│  ├─ bootstrap/                   # composition root and wiring
│  ├─ core/                        # config and cross-cutting app concerns
│  ├─ db/                          # persistence state helpers
│  ├─ infrastructure/              # cross-feature repos and vendor adapters
│  ├─ modules/
│  │  ├─ agents/
│  │  ├─ datasets/
│  │  ├─ experiments/
│  │  ├─ exports/
│  │  ├─ policies/
│  │  ├─ runs/
│  │  ├─ execution/                # execution-plane bridge during migration
│  │  ├─ health/
│  │  └─ shared/
│  ├─ main.py
│  └─ worker.py
└─ tests/
```

Inside `app/modules/*`, the intended unit of ownership is the business module, not a global
repository-wide `domain/`, `application/`, or `adapters/` folder.

The main feature modules already follow this shape:

```text
app/modules/<feature>/
├─ domain/
├─ application/
└─ adapters/
```

That is the right mental model for areas such as:

- `experiments`
- `runs`
- `datasets`
- `exports`
- `policies`
- `agents`

The rule is:

- split the repository by platform plane
- split the control plane by business module
- split each control-plane module internally by domain, application, and adapters

## What Does Not Use Hexagonal Design

Execution, ingestion, and other pipeline-oriented subsystems should not be forced into the same
mental model as the control plane.

Apply different ownership rules to these areas:

- `runtimes/runner-*` owns runner bootstrap, framework adapters, event mapping, and artifact
  upload concerns
- `apps/data-ingestion/` owns event normalization, trajectory rebuilding, enrichment, and writes
- `apps/eval-worker/` owns evaluation execution and batch scoring
- `apps/export-worker/` owns export materialization, sharding, and manifest generation

These are orchestration or data-pipeline concerns first. They can have clean boundaries without
pretending the whole repository is one large hexagon.

## Shared Contract Boundary

The most important shared boundary is the contracts layer.

Current implementation:

- `packages/contracts/python/` is the concrete shared package consumed by Python services today
- `schemas/jsonschema/`, `schemas/openapi/`, and `schemas/protobuf/` reserve the neutral schema
  space for cross-language evolution

Directionally, contracts such as `RunSpec`, event envelopes, artifact metadata, eval results, and
export manifests should live in shared packages or schemas, not as private control-plane models and
not as runtime-specific SDK objects.

That includes observability handoff. Runtime payloads may carry neutral observability configuration,
but runtimes should still treat OTLP as the transport boundary and keep vendor-specific read-side
linking outside the runtime layer.

## Web And Frontend Layout

The frontend follows the same top-level monorepo rule while using its own internal layering:

```text
apps/web/
├─ app/                            # App Router entrypoints
├─ src/
│  ├─ widgets/
│  ├─ features/
│  ├─ entities/
│  └─ shared/
└─ test/
```

This is intentionally different from the control plane. The frontend is not structured as a
hexagonal backend; it is a thin-route, layered UI application.

## Current Status

The repository is already aligned with the recommended direction, but it is still transitional in a
few places:

- `apps/control-plane/` and `apps/web/` are the most active applications
- `packages/contracts/python/` is the concrete shared contracts package in use today
- `runtimes/` and several worker apps exist as explicit landing zones so new execution or
  data-plane code does not drift back into the control-plane service
- some control-plane execution and eval concerns still live in transitional modules while the
  runtime and pipeline boundaries continue to sharpen

When adding new code, prefer preserving that direction rather than creating new top-level
`backend/`, `frontend/`, or repository-wide hexagonal layer folders.
