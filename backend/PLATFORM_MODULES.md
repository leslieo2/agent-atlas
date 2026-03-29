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
- `app/modules/artifacts/`
- `app/modules/runs/` for run registry, lineage, and control-plane lifecycle semantics

Typical control-plane objects:

- `DatasetVersion`
- `Experiment`
- `RunRecord`
- `EvalResult`
- `ExportBatch`
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

- `app/execution_plane/`

Primary concerns:

- runner-facing contracts
- launcher bootstrap layout
- orchestration and state machine work
- local and Kubernetes carrier launch

Key rule:

- the execution plane manages runtime contracts, not Python or TypeScript specific SDK objects

### Observability And Ingestion

Current locations:

- `app/modules/traces/`
- `app/infrastructure/adapters/trace_projection/`
- `app/infrastructure/adapters/trajectory_projection.py`
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

## Current Repo Mapping

Use this split when adding code:

- Atlas business workflows: `app/modules/*`
- execution runtime contracts and launchers: `app/execution_plane/*`
- vendor or backend integrations: `app/infrastructure/adapters/*`
- persistence implementations: `app/infrastructure/repositories/*`

## Direction

The current codebase is still transitional in a few places:

- `app/modules/runs/application/execution.py` still contains hot-path execution orchestration
- `app/modules/traces/` still mixes control-plane and ingestion concerns

Directionally, those hot-path and ingestion-heavy pieces should keep moving toward dedicated
execution-plane and pipeline-oriented subsystems.
