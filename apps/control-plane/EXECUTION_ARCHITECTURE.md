# Execution Subsystem

This document describes the execution subsystem inside the Agent Atlas control-plane backend.

`app/execution/` is not a feature module like `agents`, `datasets`, or `experiments`.
It is a dedicated orchestration subsystem that sits between Atlas-owned run intent and the
execution-side runtime packages under `../../runtimes/`.

## Responsibilities

The execution subsystem owns:

- execution submission, retry, cancel, and status orchestration
- translation from control-plane run submission into the external `RunnerRunSpec` contract
- runner backend selection and dispatch
- launcher and carrier integration such as local and Kubernetes launch requests
- execution-side result persistence hooks back into control-plane run state

The execution subsystem does not own:

- run registry or business-level run semantics
- dataset, experiment, export, or policy workflows
- framework-specific runtime execution logic
- raw trace browsing or observability backend UX

## Boundary Model

The intended relationship is:

```text
app/modules/runs + app/modules/experiments
                |
                v
          app/execution
                |
                v
            runtimes/*
```

Interpret that flow as:

- `runs` owns run records, lifecycle semantics, and Atlas-owned provenance fields
- `experiments` owns batch fan-out and aggregation decisions
- `execution` owns orchestration and carrier-facing dispatch
- `runtimes/*` owns framework-specific execution and runtime-side trace/event mapping

The default production target for execution is Kubernetes container runtime. External systems such
as Inspect AI and E2B belong behind execution adapters and must map into Atlas-neutral runner,
event, terminal-result, and artifact-manifest contracts.

## Internal Layout

`app/execution/` uses lightweight subsystem layering:

```text
app/execution/
├─ application/     # orchestration entrypoints and ports
├─ domain/          # execution handles, status snapshots, capabilities
├─ adapters/        # launchers, runner registry, and submission-to-runner translation
└─ service.py       # hot-path execution flow and result projection
```

Use the layers as follows:

### `application/`

Owns:

- ports such as `ExecutionControlPort`
- orchestration-facing entrypoints consumed by control-plane modules

### `domain/`

Owns thin execution-state models such as:

- `RunHandle`
- `RunStatusSnapshot`
- `RunTerminalSummary`
- `ExecutionCapability`
- `CancelRequest`

This domain should stay intentionally small. Execution is an orchestration subsystem, not a
business domain with deep aggregates.

### `adapters/`

Owns:

- `control.py` for submission, retry, cancel, and status orchestration adapters
- `runner.py` for runner backend dispatch and published artifact resolution
- `specs.py` for control-plane to runner contract translation
- `launchers/` for local and Kubernetes carrier adapters

## Dependency Rules

Execution code may depend on:

- `app/modules/runs/*` domain models and application ports where Atlas-owned run state is required
- `app/modules/shared/*` shared enums, tasks, and low-level shared models
- `packages/contracts/python` for neutral execution and runtime contracts
- `runtimes/*` only through shared contracts and launcher/bootstrap utilities, not through
  framework-specific SDK objects in the control-plane codepath

Execution code should not depend on:

- API route code
- frontend transport schemas
- feature-module use cases from `agents`, `datasets`, `experiments`, or `exports`
- Phoenix-specific runtime contracts

Feature modules should depend on `app/execution/application` ports, not on launcher or runner
implementation details in `app/execution/adapters`.

## Runtime Contract Boundary

The shared contract boundary lives in `../../packages/contracts/python`.

Execution is the place where control-plane models become:

- `RunnerRunSpec`
- launcher bootstrap requests

That translation must stay centralized in `app/execution/contracts.py` so that:

- control-plane business modules do not learn runner payload shape
- runtime packages do not import control-plane internals
- future carrier or runner backend changes stay localized
- Kubernetes resource identity, Inspect AI objects, and E2B session objects do not leak into Atlas
  business semantics

## Tracing And Observability

Execution may attach neutral tracing configuration to runner payloads, but it does not own the
observability backend.

Rules:

- execution can hand off OTLP-side tracing config
- runtimes emit runtime-side events and OTLP traces
- control-plane tracing adapters own query, link, and projection concerns
- Phoenix remains an optional read-side backend, not the execution contract
- external systems may contribute adapter-specific evidence, but Atlas evidence remains canonical

## Extension Guidance

When adding new execution functionality:

- put orchestration and state transition behavior in `app/execution/`
- keep feature-specific business decisions in `app/modules/*`
- keep framework-specific runtime behavior in `../../runtimes/`
- keep new carriers behind adapters and launcher interfaces

If execution grows into a separate deployable service later, `app/execution/` should be the seam
you extract from, not `app/modules/runs/`.
