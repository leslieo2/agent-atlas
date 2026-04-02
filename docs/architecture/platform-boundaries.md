# Platform Boundaries

This document defines the target repository and deployment boundaries for the main Atlas planes:

- control plane
- execution plane
- runner plane
- agent tracing and observability plane
- data plane

The goal is to remove ambiguity about where code belongs, what can depend on what, and which
systems are allowed to shape Atlas-owned semantics.

If you want the compact platform picture first, start with
[overview.md](overview.md). This document is the detailed ownership and dependency version of that
same model.

## Boundary Freeze Stance

Atlas is converging on two stable centers:

- a neutral control plane
- a canonical evidence and data plane

Execution and external tooling integrate around those centers, not through them.

The frozen platform contract surface is:

- run submission
- cancel, status, and heartbeat
- event ingest
- terminal result
- artifact manifest

The long-lived Atlas objects are:

- `PublishedAgentSnapshot`
- `RunRecord`
- `RunEvidence`
- `SampleOutcome`
- `ExperimentResult`
- `ExportRecord`

Every execution carrier or external system must map into those contracts and objects.

That means:

- Kubernetes is the primary execution implementation, but Kubernetes resources do not become
  Atlas core models
- Inspect AI and E2B are adapter integrations, not platform centers
- no external runtime, sandbox, or observability system is allowed to reverse-shape the Atlas
  domain model

## Current Assessment

The repository already has a strong internal structure:

- control-plane feature logic is modularized under `apps/control-plane/app/modules`
- execution orchestration is isolated under `apps/control-plane/app/execution`
- trace ingestion and projection are isolated under `apps/control-plane/app/agent_tracing`
- runner framework code is isolated under `runtimes/runner-*`
- cross-plane payloads already have a neutral home in `packages/contracts/python`

The main architectural gap is not naming. It is runtime ownership and model authority.

Today, the default local execution path still executes published runtimes from inside the
control-plane process. That means the repository has a clean conceptual split, but not yet a hard
runtime boundary between control plane and execution adapters.

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
- canonical Atlas records such as `PublishedAgentSnapshot`, `RunRecord`, `SampleOutcome`, and
  `ExportRecord`
- execution intent, not carrier mechanics

Must not own:

- framework SDK execution
- container bootstrap
- OTLP span emission from a live runner
- trajectory rebuilding pipelines
- carrier-native object models such as Kubernetes `Job` shapes or E2B session objects

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

- runner request validation
- queue consumption and worker lifecycle
- run state transitions driven by execution outcomes
- backend selection for carriers and adapter integrations
- the primary Kubernetes container runtime path

Must not own:

- business policy for datasets, exports, or experiments
- framework-specific SDK logic
- trace backend query APIs
- Atlas-first domain objects that bypass the canonical evidence model

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

Important rule:

- Kubernetes container execution is the default implementation target
- Inspect AI, E2B, and similar systems belong behind adapter interfaces in this plane
- adapters may enrich runner requests and evidence mapping, but they must emit Atlas-neutral records

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
- observability backends project into `RunEvidence`; they do not define the evidence schema

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
keeps ownership of governance metadata and operator intent. The data plane is the canonical home
for evidence normalization rather than a mirror of any one execution or observability backend.

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
- `apps/control-plane/app/modules/* -> Kubernetes SDK object models`
- `apps/control-plane/app/modules/* -> Inspect AI or E2B SDK object models`

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

### Phase 1: Freeze Platform Boundaries

Freeze the primary Atlas contract and object model before moving more runtime code around.

Do:

- keep the primary contract limited to run submission, cancel, status, heartbeat, event ingest,
  terminal result, and artifact manifest
- converge Atlas-owned long-lived records on `PublishedAgentSnapshot`, `RunRecord`,
  `RunEvidence`, `SampleOutcome`, `ExperimentResult`, and `ExportRecord`
- keep `packages/contracts/python` as the only required runner-facing contract package
- keep control-plane read models private to control-plane modules
- make every carrier or vendor integration map into Atlas records instead of adding new Atlas core
  objects

Do not:

- move vendor-specific Phoenix query adapters into shared packages
- add Kubernetes, Inspect AI, or E2B concepts as first-class product models

Success condition:

- Atlas can add or swap adapters without changing its core product objects
- Kubernetes can be the default execution path without Kubernetes resource identity leaking into
  Atlas semantics

### Phase 2: Make Runner Execution Truly External

Replace in-process default execution with an out-of-process runner path.

Do:

- treat `local-process` as a development fallback only
- make Kubernetes container runtime the production-default execution path
- keep any Inspect AI or E2B support behind adapter boundaries
- make execution and runners talk through `RunnerRunSpec` plus terminal artifacts only

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
