# Platform Boundaries

This document defines the target repository and deployment boundaries for the main Atlas planes:

- control plane
- execution plane
- runner plane
- agent tracing and observability plane
- data plane

The goal is to remove ambiguity about where code belongs and what can depend on what.

## Current Assessment

The repository already has a strong internal structure:

- control-plane feature logic is modularized under `apps/control-plane/app/modules`
- execution orchestration is isolated under `apps/control-plane/app/execution`
- trace ingestion and projection are isolated under `apps/control-plane/app/agent_tracing`
- runner framework code is isolated under `runtimes/runner-*`
- cross-plane payloads already have a neutral home in `packages/contracts/python`

The main architectural gap is not naming. It is runtime ownership.

Today, the default local execution path still executes published runtimes from inside the
control-plane process. That means the repository has a clean conceptual split, but not yet a hard
runtime boundary between control plane and runner plane.

## Target Ownership Model

Use one rule everywhere:

- a plane owns code when it owns the runtime process, failure mode, scaling decision, and release
  cadence for that code

That yields the following target split.

### 1. Control Plane

Owns:

- agents, datasets, experiments, exports, policies, and run submission semantics
- control-plane APIs and operator-facing state
- publication, provenance, and policy decisions
- execution intent, not execution mechanics

Must not own:

- framework SDK execution
- container bootstrap
- OTLP span emission from a live runner
- trajectory rebuilding pipelines

Target location:

```text
apps/control-plane/
├─ app/api/
├─ app/bootstrap/
├─ app/core/
├─ app/modules/
│  ├─ agents/
│  ├─ datasets/
│  ├─ experiments/
│  ├─ exports/
│  ├─ policies/
│  ├─ runs/
│  └─ shared/
└─ tests/
```

Keep in the control plane only what is required to govern and query the system.

### 2. Execution Plane

Owns:

- execution handoff validation
- queue consumption and worker lifecycle
- run state transitions driven by execution outcomes
- backend selection for local, container, or Kubernetes carriers

Must not own:

- business policy for datasets, exports, or experiments
- framework-specific SDK logic
- trace backend query APIs

Target location:

```text
apps/executor-gateway/
├─ app/control/
├─ app/scheduler/
├─ app/workers/
├─ app/backends/
└─ tests/
```

Short term, `apps/control-plane/app/execution` remains the transitional home. Long term, this code
should move out when worker deployment and backend control become independently operated concerns.

### 3. Runner Plane

Owns:

- framework-specific agent loading
- runtime SDK calls
- per-framework trace mapping
- bootstrap IO such as reading run spec, writing events, and writing terminal results

Must not own:

- control-plane repositories
- FastAPI wiring
- run query/read models
- Phoenix query clients or Atlas state mutation

Target location:

```text
runtimes/
├─ runner-base/
├─ runner-openai-agents/
├─ runner-langgraph/
└─ runner-<framework>/
```

The runner plane should consume only:

- `packages/contracts/*`
- runner-local helper packages
- framework SDK dependencies

The runner plane should never import `apps/control-plane/app/*`.

### 4. Agent Tracing And Observability Plane

Owns:

- trace ingest normalization
- OTLP export coordination
- trace storage adapters
- trace link resolution and backend-specific read-side lookups

Must not own:

- run submission
- framework execution
- dataset or experiment business logic

Target split:

```text
apps/data-ingestion/
├─ app/ingest/
├─ app/normalize/
├─ app/export/
└─ tests/

packages/observability-contracts/
└─ src/
```

Important rule:

- write-side telemetry contracts must be neutral and shared
- backend-specific read-side integrations such as Phoenix links stay outside runner packages

This is the area where the current code is still transitional. `app/agent_tracing/contracts.py`
currently acts as the source of truth for protocols that are effectively shared across planes.

### 5. Data Plane

Owns:

- trajectory storage
- artifact metadata
- replayable step records
- labeling, enrichment, and training-oriented normalization

Must not own:

- FastAPI control-plane business workflows
- framework SDK execution
- vendor-specific observability SDK logic

Target location:

```text
apps/data-plane-api/
├─ app/api/
├─ app/storage/
├─ app/query/
└─ tests/

apps/export-worker/
apps/eval-worker/
```

This plane should become the long-term owner of training-usable records, while the control plane
keeps ownership of governance metadata and operator intent.

## Dependency Rules

The target dependency graph is:

```text
apps/web -> apps/control-plane -> packages/contracts
apps/control-plane -> apps/executor-gateway -> packages/contracts
apps/executor-gateway -> runtimes/runner-* -> packages/contracts
apps/data-ingestion -> packages/contracts
apps/data-plane-api -> packages/contracts
```

And the forbidden reverse edges are:

- `runtimes/runner-* -> apps/control-plane`
- `apps/data-ingestion -> apps/control-plane/app/modules/*`
- `apps/control-plane/app/modules/* -> runtimes/runner-*`
- `apps/control-plane/app/modules/* -> tracing backend SDKs`

## Recommended Repository Layout

The target layout for the next split is:

```text
agent-atlas/
├─ apps/
│  ├─ web/
│  ├─ control-plane/
│  ├─ executor-gateway/
│  ├─ data-ingestion/
│  ├─ data-plane-api/
│  ├─ export-worker/
│  └─ eval-worker/
├─ packages/
│  ├─ contracts/
│  ├─ observability-contracts/
│  ├─ runtime-sdk/
│  └─ testkit/
├─ runtimes/
│  ├─ runner-base/
│  ├─ runner-openai-agents/
│  └─ runner-langgraph/
├─ infra/
├─ schemas/
└─ docs/
```

## What Should Move First

The migration should happen in this order.

### Phase 1: Harden Contracts

Move shared tracing and execution protocols to neutral packages.

Do:

- move shared trace ingest and export protocols out of `app/agent_tracing/contracts.py`
- keep `packages/contracts/python` as the only required runner-facing contract package
- keep control-plane read models private to control-plane modules

Do not:

- move vendor-specific Phoenix query adapters into shared packages

### Phase 2: Make Runner Execution Truly External

Replace in-process default execution with an out-of-process runner path.

Do:

- treat `local-process` as a development fallback only
- add a real local worker or container runner that invokes runner packages as a separate process
- make control-plane and worker talk through execution handoff plus terminal artifacts only

Success condition:

- a framework crash cannot take down the control-plane API process

### Phase 3: Split Execution Gateway

Extract queue-backed execution orchestration from `apps/control-plane/app/execution`.

Do:

- move backend selection and submission control into `apps/executor-gateway/`
- keep control-plane ownership of run intent and operator-facing status APIs
- keep execution worker ownership of leases, heartbeats, retries, and carrier adapters

Success condition:

- execution workers can be deployed, scaled, and rolled independently of API releases

### Phase 4: Split Tracing And Data Pipelines

Extract write-heavy telemetry and normalization paths.

Do:

- move trace ingestion, normalization, and projection out of the control-plane process
- leave query and trace-link read facades in control-plane only if they are strictly read-side
- move trajectory rebuilding and artifact shaping to data-plane-oriented workers

Success condition:

- high-volume telemetry traffic no longer shares process resources with control-plane APIs

## Concrete Rules For New Code

When adding new code now:

1. If it governs Atlas business semantics, put it under `apps/control-plane/app/modules/*`.
2. If it executes a framework SDK, put it under `runtimes/runner-*`.
3. If it is a shared wire contract, put it under `packages/contracts/*`.
4. If it is trace normalization or trajectory shaping, avoid putting it into control-plane feature
   modules.
5. If it needs independent scale or failure isolation, do not add it to `apps/control-plane/app/*`
   unless it is explicitly temporary.

## Immediate Cleanup Targets In This Repository

These are the highest-value boundary cleanups for the current tree:

- make `app.modules.shared.application.contracts` the source of truth instead of a re-export shim
- stop using the control-plane process as the default published-agent runner
- keep `app.execution` free of framework package imports and keep `runtimes/` free of control-plane
  imports
- move any future trace protocol growth into neutral shared contracts instead of expanding
  `app.agent_tracing.contracts`

## Decision Checklist

Before creating a new module, answer these questions:

1. Which process owns the failure if this code crashes?
2. Which service should scale when this code gets hot?
3. Which team boundary or deployment boundary should own releases for it?
4. Is the API here business semantics, execution semantics, or telemetry semantics?
5. Could a runner package or data worker import this without pulling in control-plane internals?

If those answers are unclear, the code probably does not have a clean plane boundary yet.
