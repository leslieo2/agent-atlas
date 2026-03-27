# Backend Architecture

This document describes the current backend architecture for Agent Atlas.

It is intentionally practical. The goal is to explain the dependency rules that the codebase
actually follows today, not to describe a hypothetical future design.

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

Business logic belongs in feature modules. Infrastructure implements ports owned by those
modules. Routes handle HTTP concerns only.

The module boundaries are enforced by architecture tests under `backend/tests/unit/`.

## Design Goals

This architecture is optimized for the current product shape:

- a single control-plane backend
- clear feature ownership
- low ceremony for a small team
- explicit boundaries for runs, traces, agents, evals, datasets, and exports
- the ability to swap infrastructure implementations without moving business logic

This is not a microservice architecture. For v1, the backend should stay a single deployable
service.

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
- `TraceCommands`, `TraceIngestionWorkflow`
- `EvalJobCommands`, `EvalExecutionService`, `EvalAggregationService`
- `AgentDiscoveryQueries`, `AgentPublicationCommands`

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

Not every feature needs a rich domain layer. Some modules are mostly application-oriented and use
domain models only as contracts.

### 4. Infrastructure layer

Location: `app/infrastructure/`

Responsibilities:

- repository implementations
- runtime adapters
- export adapters
- trace projection adapters
- task queue implementations
- cross-feature gateway adapters
- SDK-specific agent loading and validation

Infrastructure may depend on module ports and domain models. The reverse must not happen.

#### Repositories vs adapters

`app/infrastructure/repositories/` contains persistence implementations:

- `StateRunRepository`
- `StateTrajectoryRepository`
- `StateTraceRepository`
- `StateDatasetRepository`
- `StateEvalJobRepository`
- `StateEvalSampleResultRepository`
- `StatePublishedAgentRepository`
- `StateArtifactRepository`
- `StateSystemStatus`

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

Adapter organization follows the same rule:

- keep SDK-agnostic or feature-agnostic adapter services near `app/infrastructure/adapters/`
- keep vendor-specific code in nested packages such as
  `app/infrastructure/adapters/openai_agents/` or `app/infrastructure/adapters/langchain/`
- keep persistence adapters under `app/infrastructure/repositories/`
- do not mix generic orchestration with SDK object validation, SDK response parsing, or
  provider-specific runtime setup in the same file

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
bundle type next to its builder:

- `infrastructure.py`: repositories and low-level adapters
- `agents.py`, `traces.py`, `datasets.py`, `runs.py`, `evals.py`, `artifacts.py`, `health.py`:
  feature wiring
- `worker.py`: worker wiring

`bootstrap/providers/` contains thin dependency-provider functions such as
`get_container().runs.run_queries`, so route imports do not need to point back into
`container.py`.

## Feature Modules

Feature modules live under `app/modules/`.

### `runs`

Owns:

- run lifecycle
- run creation and termination
- submission of queued run work
- runtime execution workflow
- run-owned execution telemetry read models such as trajectory
- run-scoped query aggregation, including trace lookup for run detail views

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
- trace span projection
- trace persistence port

Examples:

- `TraceCommands`
- `TraceIngestionWorkflow`
- `TraceProjectorPort`
- `TraceRepository`

### `agents`

Owns:

- agent discovery and publication workflows
- published agent metadata
- runnable agent catalog contracts
- agent framework metadata used by run submission

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
- contracts for reading run outcomes

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

This avoids turning one feature module into a hidden shared layer.

## Data and Control Flow

### Run flow

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
  -> TraceProjectorPort.project
  -> TraceRepository.append
  -> TrajectoryStepProjectorPort.project(...)
  -> TrajectoryRepository.append(...)
  -> RunRepository.save(updated status/metrics)
```

### Trace ingestion flow

```text
POST /traces/ingest
  -> RunTelemetryIngestionService.ingest
  -> TraceIngestionPort.ingest
  -> TraceProjectorPort.project
  -> TraceRepository.append
  -> TrajectoryStepProjectorPort.project(...)
  -> TrajectoryRepository.append(...)
```

### Agent publication flow

```text
POST /agents/{agent_id}/publish
  -> AgentPublicationCommands.publish
  -> AgentSourceDiscoveryPort.list_agents
  -> PublishedAgentRepositoryPort.save_agent
```

### Eval flow

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

### Artifact export flow

```text
POST /artifacts/export
  -> ArtifactCommands.export
  -> ArtifactExportPort.export
  -> RunLookupSource.get
  -> TrajectoryExportSource.list_for_run
  -> ArtifactRepository.save
```

## Current Infrastructure Notes

The current backend uses state-backed repository implementations behind
`app/infrastructure/repositories/`.

The lower-level state machinery under `app/db/` is infrastructure-private support code. It should
be treated as an implementation detail, not as a separate business layer.

If the backend later moves to Postgres, external object storage, or external trace storage, the
change should primarily happen by replacing infrastructure implementations, not by moving business
logic out of modules.

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

## How To Add A New Feature

When adding a new backend capability:

1. Create or extend a feature module under `app/modules/`.
2. Put domain models and rules in `domain/`.
3. Put use cases and required ports in `application/`.
4. Put HTTP request/response schemas in `contracts/` if the feature is exposed over HTTP.
5. Put persistence implementations in `app/infrastructure/repositories/`.
6. Put non-persistence infrastructure implementations in `app/infrastructure/adapters/`.
7. Wire everything in `app/bootstrap/container.py`.
8. Add or extend architecture tests if a new boundary rule needs protection.

When wiring grows, prefer adding or updating a builder in `app/bootstrap/wiring/` instead of
putting more assembly detail back into `container.py`.

## What Not To Do

Avoid these patterns:

- adding new business logic under top-level `app/application`, `app/domain`, or `app/models`
- importing `app.infrastructure` from module domain code
- importing another feature's `application.use_cases` or `application.execution`
- putting persistence code into feature domain modules
- putting every reusable protocol into `runs`
- adding broad "shared services" abstractions without a concrete cross-feature need

## Scope Note

This document describes the code that exists today. Earlier drafts mentioned replay workflows, but
the current backend does not contain a `replays` module. If replay support is added later, it
should follow the same module and port ownership rules described here.
