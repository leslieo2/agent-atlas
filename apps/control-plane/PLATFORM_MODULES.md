# Backend Module Split

This repository should not describe the whole product as one giant hexagonal application.

The product is a layered platform:

- control plane
- execution plane
- observability and eval plane
- data plane
- training plane

Inside that platform, only the control-plane services should default to hexagonal design.

## What Uses Hexagonal Design

These areas own Atlas business semantics and should stay centered on domain objects, use cases, and
stable ports:

- `app/modules/agents/`
- `app/modules/datasets/`
- `app/modules/experiments/`
- `app/modules/policies/`
- `app/modules/exports/`
- `app/modules/runs/` for run registry, lineage, and control-plane lifecycle semantics

Typical control-plane objects:

- `PublishedAgentSnapshot`
- `RunRecord`
- `RunEvidence`
- `SampleOutcome`
- `ExperimentResult`
- `ExportRecord`
- `ApprovalPolicy`

Typical control-plane ports:

- execution control
- trace backend
- artifact store
- framework registry
- task queue

## What Does Not Use Hexagonal Design

These areas should be designed as orchestration systems, event pipelines, or data processing
subsystems instead of forcing them into a ports-and-adapters mental model.

### Execution Plane

Location:

- `app/execution/`

Primary concerns:

- runner-facing contracts
- launcher bootstrap layout
- orchestration and state machine work
- local and Kubernetes carrier launch

Key rule:

- the execution plane manages runtime contracts, not Python or TypeScript specific SDK objects
- it remains under `apps/control-plane/app/` while it shares the control-plane process, wiring,
  and repositories; conceptual plane boundaries do not automatically imply top-level directories
- Kubernetes is the primary execution implementation
- Inspect AI, E2B, and similar systems must appear here only as adapters, never as Atlas core
  models

### Observability And Ingestion

Current locations:

- `app/agent_tracing/`
- `app/data_plane/`
- `app/infrastructure/adapters/phoenix.py`

These are better understood as event collection, normalization, export, and projection pipelines.

### Data Plane

Current and future locations:

- trajectory projection and storage
- artifact indexing
- sample curation
- reward aggregation
- export lineage enrichment

These are data pipeline and storage workflows, not pure domain-service adapters.

## Placement Rule

Choose the directory by runtime ownership:

- keep code in `app/modules/*` when it owns Atlas business semantics
- keep code in `app/execution/`, `app/agent_tracing/`, or `app/data_plane/` when it is an
  in-process orchestration or pipeline subsystem
- move code to `packages/` only when multiple apps or runtimes must import it as a shared library
- move definitions to `schemas/` only when they should remain language-neutral
- move code to repository-level runtime areas only when it can evolve outside the control-plane
  process

## Current Repo Mapping

Use this split when adding code:

- Atlas business workflows: `app/modules/*`
- feature-local inbound and outbound adapters: `app/modules/<feature>/adapters/*`
- execution orchestration, runtime contracts, and launchers: `app/execution/*`
- vendor or backend integrations: `app/infrastructure/adapters/*`
- persistence implementations: `app/infrastructure/repositories/*`

## Direction

The current codebase is still transitional in a few places, especially around tracing and
ingestion-heavy flows. Directionally, orchestration-heavy execution code belongs in
`app/execution/`, while ingestion-heavy pieces should keep moving toward `app/agent_tracing/` and
`app/data_plane/` subsystems.
