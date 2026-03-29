# Backend Architecture

This document describes the backend architecture for Agent Atlas.

It stays intentionally practical. The goal is to explain the dependency rules that the codebase
follows today and the extension rules that should guide the next stage of work.

## Summary

The backend is a modular monolith built with FastAPI and organized around feature modules.

Primary locations:

- `app/api/routes/`: HTTP entrypoints
- `app/modules/*`: feature-owned business code
- `app/infrastructure/repositories/`: persistence implementations
- `app/infrastructure/adapters/`: non-persistence infrastructure adapters
- `app/bootstrap/container.py`: composition root entrypoint
- `app/bootstrap/wiring/`: object graph assembly helpers
- `app/bootstrap/providers/`: FastAPI dependency providers

The core dependency direction is:

```text
HTTP/API -> application -> domain
                    |
                    v
             infrastructure
```

More concretely:

```text
app/api/routes -> app/modules/*/(contracts, application, domain)
app/bootstrap/container -> app/bootstrap/wiring/* -> app/modules/* + app/infrastructure/*
app/infrastructure/* -> app/modules/* application ports and domain models
```

Business logic belongs in feature modules. Infrastructure implements ports owned by those modules.
Routes handle HTTP concerns only.

The module boundaries are enforced by architecture tests under `backend/tests/unit/`.

## Design Goals

This architecture is optimized for the current and next-stage product shape:

- a single control-plane backend
- clear feature ownership
- low ceremony for a small team
- explicit boundaries for agents, runs, traces, evals, datasets, and exports
- the ability to swap runtime, runner, queue, and observability implementations without moving
  business logic out of modules
- a clean split between Atlas-owned control-plane state and external observability backends such as
  Phoenix

This is not a microservice architecture. The backend should stay a single deployable service unless
that constraint becomes the actual bottleneck.

## Layer Model

### 1. API layer

Location: `app/api/routes/`

Responsibilities:

- define HTTP routes
- parse request parameters and bodies
- map errors to HTTP responses
- call application use cases
- map domain objects to transport contracts

Non-responsibilities:

- business policy
- persistence logic
- runtime integration details
- vendor-specific observability SDK wiring

### 1a. Contracts layer

Location: `app/modules/<feature>/contracts/`

Responsibilities:

- define feature-local request and response schemas
- map domain objects into HTTP-safe payloads
- convert inbound payloads into application or domain inputs

Non-responsibilities:

- declaring FastAPI routes
- performing dependency injection
- importing infrastructure or storage details

### 2. Application layer

Location: `app/modules/<feature>/application/`

Responsibilities:

- implement use cases
- orchestrate domain objects
- define required ports
- coordinate feature workflows

Examples in the current codebase:

- `RunCommands`, `RunQueries`, `RunExecutionService`, `RunSubmissionService`
- `TraceCommands`, `RunTelemetryIngestionService`
- `EvalJobCommands`, `EvalExecutionService`, `EvalAggregationService`
- `AgentDiscoveryQueries`, `AgentPublicationCommands`

Planned additions should follow the same rule:

- framework registry orchestration stays in feature-owned application code
- runner selection stays behind application-owned ports
- Phoenix or OTLP clients stay in infrastructure

### 3. Domain layer

Location: `app/modules/<feature>/domain/`

Responsibilities:

- business state
- invariants
- state transition rules
- value objects and domain models

Non-responsibilities:

- FastAPI
- persistence details
- task queue implementations
- SDK-specific runtime code
- filesystem or package scanning
- vendor SDK clients

Not every feature needs a rich domain layer. Some modules are mostly application-oriented and use
domain models only as contracts.

### 4. Infrastructure layer

Location: `app/infrastructure/`

Responsibilities:

- repository implementations
- runtime adapters
- artifact export adapters
- future artifact build and image-resolution adapters
- future runner adapters
- trace projection adapters
- task queue implementations
- cross-feature gateway adapters
- SDK-specific agent loading and validation
- future Phoenix and OTLP export adapters

Infrastructure may depend on module ports and domain models. The reverse must not happen.

#### Repositories vs adapters

`app/infrastructure/repositories/` contains persistence implementations for Atlas-owned state:

- runs
- trajectories
- traces
- datasets
- eval jobs and sample results
- published agents
- artifacts
- health and system status

`app/infrastructure/adapters/` contains other infrastructure implementations that are not simple
record persistence:

- runtime dispatch in `runtime.py`
- OpenAI Agents SDK integration in `openai_agents/`
- LangChain runtime integration in `langchain/`
- task queue implementation in `task_queue.py`
- trace projection in `trace_projection/`
- trajectory projection in `trajectory_projection.py`
- eval gateway and agent lookup adapters in `evals/`
- artifact export adapter in `artifacts.py`
- filesystem agent discovery and runnable catalog assembly in `agent_catalog.py`

Future external integrations should follow the same pattern:

- keep SDK-agnostic or feature-agnostic adapter services near `app/infrastructure/adapters/`
- keep vendor-specific code in nested packages such as `app/infrastructure/adapters/openai_agents/`
  or a future `app/infrastructure/adapters/phoenix/`
- keep persistence adapters under `app/infrastructure/repositories/`
- do not mix generic orchestration with SDK object validation, SDK response parsing, or
  provider-specific setup in the same file

### 5. Composition root

Primary locations:

- `app/bootstrap/container.py`
- `app/bootstrap/wiring/`
- `app/bootstrap/providers/`

Responsibilities:

- keep the top-level composition root small and readable
- instantiate repositories and adapters through wiring helpers
- hold module-level bundles instead of a flat global object registry
- expose dependency providers for FastAPI through thin provider modules
- assemble the worker object graph

`container.py` remains the only public composition root. The lower-level assembly details live in
`bootstrap/wiring/`, which groups object graph construction by concern and keeps each module's
bundle type next to its builder.

## Feature Modules

Feature modules live under `app/modules/`.

### `runs`

Owns:

- run lifecycle
- run creation and termination
- submission of queued run work
- runtime execution workflow
- runner-facing execution control contracts
- run-owned execution telemetry read models such as trajectory
- run-scoped query aggregation, including trace lookup for run detail views
- execution provenance such as backend, artifact, and failure metadata

Examples:

- `RunCommands`
- `RunQueries`
- `RunSubmissionService`
- `RunExecutionService`
- `RunTelemetryIngestionService`

### `traces`

Owns:

- trace ingestion workflow
- trace normalization contracts
- trace span persistence contracts
- collaboration contracts for trace projection and raw trace retrieval

Examples:

- `TraceCommands`
- `TraceRepository`
- `TraceIngestionPort`

When Phoenix integration lands, the module should still own the feature-level contracts. Phoenix
clients themselves remain in infrastructure adapters.

### `agents`

Owns:

- agent discovery and publication workflows
- published agent metadata
- runnable agent catalog contracts
- agent framework metadata used by run submission
- future artifact or image metadata attached to publication

Examples:

- `AgentDiscoveryQueries`
- `AgentPublicationCommands`
- `RunnableAgentCatalogPort`
- `PublishedAgent`

### `evals`

Owns:

- eval job lifecycle
- eval execution workflow
- eval aggregation and scoring
- eval-owned sample contracts for scoring and run fan-out
- contracts for reading run outcomes and comparison summaries

Examples:

- `EvalJobCommands`
- `EvalExecutionService`
- `EvalAggregationService`
- `EvalRunGatewayPort`

### `artifacts`

Owns:

- export use cases
- artifact metadata
- artifacts-owned export views for runs and trajectories
- future RL-ready export contracts

Examples:

- `ArtifactCommands`
- `ArtifactQueries`
- `ArtifactExportPort`
- `TrajectoryExportSource`

### `datasets`

Owns dataset CRUD and related application logic.

### `health`

Owns health and system status queries.

### `shared`

Owns only truly cross-feature primitives and protocols.

Current examples:

- shared enums in `shared/domain/`
- queued task models in `shared/domain/tasks.py`
- task queue protocol in `shared/application/`

Do not turn `shared` into a generic dumping ground.

## Port Ownership Rules

A port should be owned by the module that defines the use case needing it.

When a feature needs data from another feature, prefer a feature-owned read view or collaboration
contract over directly reusing the other feature's domain models. This keeps collaboration explicit
without pretending the modules are hard-isolated bounded contexts.

Examples:

- `TraceRepository` belongs to `traces`, because trace ingestion needs it
- `TrajectoryStepProjectorPort` belongs to `runs`, because trajectory is a run-owned read model
- `ArtifactExportPort` belongs to `artifacts`, because export is an artifacts use case
- `EvalRunGatewayPort` belongs to `evals`, because eval execution needs to fan out runs
- `TaskQueuePort` lives in `shared`, because it is a real cross-feature system protocol

For upcoming work:

- runner selection should stay behind a feature-owned application port, not leak vendor or carrier
  code into use cases
- Phoenix integration should sit behind feature-owned trace and eval read/write ports
- artifact or image build and resolution should stay behind infrastructure adapters implementing
  ports owned by the feature that consumes them

## Atlas vs External Backends

Atlas remains the source of truth for:

- published agents
- run state and lifecycle
- dataset and eval job linkage
- artifact metadata
- export provenance

External systems such as Phoenix may become the preferred backend for:

- raw spans
- deep trace exploration
- experiment-oriented observability
- prompt and evaluation inspection workflows

That split must be enforced through infrastructure adapters. Feature modules should not know whether
raw traces came from local state or from Phoenix.

## Data and Control Flow

### Current run flow

```text
POST /runs
  -> RunCommands.create_run
  -> RunnableAgentCatalogPort.get_agent(...)
  -> RunSubmissionService.submit
  -> RunRepository.save
  -> TaskQueuePort.enqueue(RUN_EXECUTION)
  -> AppWorker.run_once
  -> RunExecutionService.execute_run
  -> PublishedRunRuntimePort.execute_published(...)
  -> RunTelemetryIngestionService.ingest(...)
  -> TraceIngestionPort.ingest(...)
  -> TraceRepository.append
  -> TrajectoryStepProjectorPort.project(...)
  -> TrajectoryRepository.append(...)
  -> RunRepository.save(updated status/metrics)
```

### Current eval flow

```text
POST /eval-jobs
  -> EvalJobCommands.create_job
  -> EvalJobRepository.save
  -> TaskQueuePort.enqueue(EVAL_EXECUTION)
  -> AppWorker.run_once
  -> EvalExecutionService.execute_job
  -> EvalRunGatewayPort.create_eval_run(...)
  -> RunSubmissionService.submit
  -> TaskQueuePort.enqueue(EVAL_AGGREGATION)
  -> AppWorker.run_once
  -> EvalAggregationService.refresh_job
  -> EvalRunGatewayPort.list_eval_runs(...)
  -> EvalSampleResultRepository.save
  -> EvalJobRepository.save(completed job)
```

### Target direction for execution and observability

```text
POST /runs
  -> RunCommands.create_run
  -> RunnableAgentCatalogPort.get_agent(...)
  -> RunSubmissionService.submit
  -> resolve published snapshot -> artifact/image reference
  -> enqueue execution work
  -> worker or runner adapter executes selected artifact/image
  -> telemetry export adapter emits spans via OTel/OpenInference
  -> Phoenix stores raw spans
  -> Atlas persists run status, provenance, and export metadata
  -> Atlas returns run detail through stable REST contracts
```

## Current Infrastructure Notes

The current backend uses state-backed repository implementations behind
`app/infrastructure/repositories/`.

The lower-level state machinery under `app/db/` is infrastructure-private support code. It should
be treated as an implementation detail, not as a separate business layer.

If the backend later moves to Docker-backed runners, Phoenix-backed observability, or different
task execution infrastructure, the change should primarily happen by replacing or extending
infrastructure implementations, not by moving business logic out of modules.

## Guardrails

The intended architecture is reinforced by three mechanisms:

- repository rules in `AGENTS.md`
- dependency wiring in `app/bootstrap/container.py`
- dependency providers in `app/bootstrap/providers/`
- architecture tests in `tests/unit/test_architecture_layers.py` and
  `tests/unit/test_trace_workflow_and_architecture.py`

In practice, these rules matter most:

- business logic goes in `app/modules/*`
- routes do not talk to infrastructure directly
- domain code does not import FastAPI or storage code
- application code depends on ports, not implementations
- infrastructure implements ports owned by modules
- cross-feature imports of another feature's `application.use_cases` or
  `application.execution` are not allowed
- vendor SDKs such as Phoenix clients or framework-specific tracing helpers must stay in
  infrastructure, not feature modules

## How To Add A New Integration

When adding a new backend capability:

1. Identify the feature module that owns the use case.
2. Add or extend domain models in that module if business state changes.
3. Add or extend application ports in that module if a new infrastructure dependency is needed.
4. Implement the dependency under `app/infrastructure/`.
5. Wire everything in `app/bootstrap/container.py` through `app/bootstrap/wiring/`.
6. Add or extend architecture tests if a new boundary rule needs protection.

Examples:

- a Phoenix trace reader belongs in `app/infrastructure/adapters/phoenix/` and implements a
  feature-owned port for run-scoped trace retrieval
- a Docker runner belongs in infrastructure and is selected through a runner port, not by letting
  `RunExecutionService` import Docker SDKs directly

## What Not To Do

Avoid these patterns:

- adding new business logic under top-level `app/application`, `app/domain`, or `app/models`
- importing `app.infrastructure` from module domain code
- importing another feature's `application.use_cases` or `application.execution`
- putting persistence code into feature domain modules
- putting every reusable protocol into `runs`
- adding broad "shared services" abstractions without a concrete cross-feature need
- letting frontend-facing route code know about vendor trace backends directly

## Scope Note

This document describes the current codebase and the extension rules for the next stage. It does
not imply that Phoenix, Docker runners, or artifact-backed publication are already implemented. It
documents where those integrations should live once the code is added.
