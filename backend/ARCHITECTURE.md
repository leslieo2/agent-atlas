# Backend Architecture

This document describes the current backend architecture for Agent Flight Recorder.

It is intentionally practical. The goal is to make the codebase easier to navigate, explain the dependency rules, and reduce ambiguity when adding new features.

## Summary

The backend is a modular monolith built with FastAPI.

It uses:

- `app/api/routes/` for HTTP entrypoints
- `app/modules/*` for feature logic
- `app/infrastructure/` for outbound adapters and repositories
- `app/bootstrap/container.py` as the composition root

The core dependency direction is:

```text
HTTP/API -> application -> domain
                    |
                    v
             infrastructure
```

More concretely:

```text
app/api/routes -> app/modules/*/(api, application, domain)
app/bootstrap/container -> app/modules/* + app/infrastructure/*
app/infrastructure/* -> app/modules/* application ports and domain models
```

Business logic belongs in feature modules. Infrastructure implements ports owned by those modules. Routes handle HTTP concerns only.
The core module boundaries are also enforced by architecture tests under `backend/tests/unit/`.

## Design Goals

This architecture is optimized for the current product shape:

- a single control-plane backend
- clear feature ownership
- low ceremony for a small team
- explicit boundaries for run, trace, replay, eval, and export flows
- the ability to swap infrastructure implementations without moving business logic

This is not a microservice architecture. For v1, the backend should stay a single deployable service.

## Layer Model

### 1. API layer

Location: `app/api/routes/`

Responsibilities:

- define HTTP routes
- parse request parameters and bodies
- map errors to HTTP responses
- call application use cases
- map domain objects to API responses

Non-responsibilities:

- business policy
- persistence logic
- framework/runtime integration details

### 2. Application layer

Location: `app/modules/<feature>/application/`

Responsibilities:

- implement use cases
- orchestrate domain objects
- define ports required from infrastructure
- coordinate cross-step workflows inside a feature

This is where command/query services live, such as `RunCommands`, `RunQueries`, `ReplayCommands`, and `EvalJobCommands`.

### 3. Domain layer

Location: `app/modules/<feature>/domain/`

Responsibilities:

- business state
- invariants
- state transition rules
- value objects and domain models

Non-responsibilities:

- FastAPI
- repository implementations
- storage details
- concrete external adapters

### 4. Infrastructure layer

Location: `app/infrastructure/`

Responsibilities:

- repository implementations
- runtime adapters
- exporter adapters
- trace projection adapters
- scheduler and runner implementations

Infrastructure may depend on module ports and domain models. The reverse must not happen.

### 5. Composition root

Location: `app/bootstrap/container.py`

Responsibilities:

- instantiate repositories and adapters
- wire implementations into use cases
- expose dependency providers for FastAPI

This file is the only place where the whole object graph should be assembled.

## Feature Modules

Feature modules live under `app/modules/`.

### `runs`

Owns:

- run lifecycle
- run creation and termination
- runtime dispatch
- trajectory generation during execution

Examples:

- `RunCommands`
- `RunQueries`
- `RunExecutionService`

### `traces`

Owns:

- trace ingestion workflow
- trace normalization/projection contracts
- trace persistence port

Examples:

- `TraceCommands`
- `TraceIngestionWorkflow`
- `TraceRepository`

### `replays`

Owns:

- step replay use cases
- replay result persistence
- the read contract required to load replay baselines

Examples:

- `ReplayCommands`
- `ReplayRepository`
- `ReplayBaselineReader`

### `evals`

Owns:

- eval job lifecycle
- eval execution workflow
- evaluator contracts

Examples:

- `EvalJobCommands`
- `EvalJobRunner`
- `EvaluatorPort`

### `artifacts`

Owns:

- export use cases
- artifact metadata persistence
- the read contract required to export trajectories

Examples:

- `ArtifactCommands`
- `ArtifactExportPort`
- `TrajectoryExportSource`

### `datasets`

Owns dataset CRUD and related application logic.

### `adapters`

Owns adapter catalog queries and normalized adapter metadata.

### `health`

Owns health/system status queries.

### `shared`

Owns only truly cross-feature primitives and protocols.

Current examples:

- shared enums in `shared/domain/`
- scheduler protocol in `shared/application/`

Do not turn `shared` into a generic dumping ground.

## Port Ownership Rules

A port should be owned by the module that defines the use case needing it.

Examples:

- `TraceRepository` belongs to `traces`, because trace ingestion needs it
- `ReplayBaselineReader` belongs to `replays`, because replay needs to read baseline steps
- `TrajectoryExportSource` belongs to `artifacts`, because export needs trajectory access
- `SchedulerPort` lives in `shared`, because it is a real cross-feature system protocol

This avoids turning one feature module into a hidden shared layer.

## Data and Control Flow

### Run flow

```text
POST /runs
  -> RunCommands.create_run
  -> RunRepository.save
  -> SchedulerPort.submit
  -> RunExecutionService.execute_run
  -> RunnerRegistryPort.get_runner(...).execute(...)
  -> TrajectoryRepository.append(...)
  -> TraceRepository.append(...)
  -> RunRepository.save(updated status/metrics)
```

### Trace ingestion flow

```text
POST /traces/ingest
  -> TraceCommands.ingest
  -> TraceIngestionWorkflow.ingest
  -> TraceProjectorPort.project
  -> TraceRepository.append
```

### Replay flow

```text
POST /replays
  -> ReplayCommands.replay_step
  -> ReplayBaselineReader.list_for_run
  -> ReplayExecutor.execute
  -> ReplayRepository.save
```

### Eval flow

```text
POST /eval-jobs
  -> EvalJobCommands.create_job
  -> EvalJobRepository.save
  -> SchedulerPort.submit
  -> EvalJobRunner.run
```

### Artifact export flow

```text
POST /artifacts/export
  -> ArtifactCommands.export
  -> ArtifactExportPort.export
  -> TrajectoryExportSource.list_for_run
  -> ArtifactRepository.save
```

## Infrastructure Notes

The current backend uses in-memory/state-backed repository implementations behind `app/infrastructure/repositories/`.

The lower-level state machinery under `app/db/` is infrastructure-private support code. It should be treated as an implementation detail, not as a separate business layer.

If the backend later moves to Postgres or external trace storage, the change should primarily happen by replacing infrastructure implementations, not by moving business logic out of modules.

## Guardrails

The intended architecture is reinforced by three mechanisms:

- repository rules in `AGENTS.md`
- dependency wiring in `app/bootstrap/container.py`
- architecture tests in `tests/unit/test_trace_workflow_and_architecture.py`

In practice, these rules matter most:

- business logic goes in `app/modules/*`
- routes do not talk to infrastructure directly
- domain code does not import FastAPI or storage code
- infrastructure implements ports owned by modules
- cross-feature imports of another feature's `application.use_cases` or `application.execution` are not allowed

## How To Add A New Feature

When adding a new backend capability:

1. Create or extend a feature module under `app/modules/`.
2. Put domain models and rules in `domain/`.
3. Put use cases and required ports in `application/`.
4. Put HTTP request/response schemas in `api/` if the feature is exposed over HTTP.
5. Add repository/adapter implementations in `app/infrastructure/`.
6. Wire everything in `app/bootstrap/container.py`.
7. Add or extend architecture tests if a new boundary rule needs protection.

## What Not To Do

Avoid these patterns:

- adding new business logic under top-level `app/application`, `app/domain`, or `app/models`
- importing `app.infrastructure` from module domain code
- importing another feature's `application.use_cases` or `application.execution`
- putting every reusable protocol into `runs`
- adding broad "shared services" abstractions without a concrete cross-feature need

## Relationship To The PRD

The PRD describes a backend with clear control-plane responsibilities:

- run orchestration
- trace ingestion and normalization
- replay
- evaluation
- artifact export

This codebase maps those capabilities onto feature modules inside a single backend service. That is the intended architecture for the current stage of the product.
