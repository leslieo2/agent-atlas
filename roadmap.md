# Roadmap

## Current Product Direction

Agent Atlas is moving away from an undifferentiated "agent workbench" story and toward a more
specific control-plane role:

- repository-local agent discovery and publish / unpublish workflow
- framework-aware integration for a small set of supported runtimes
- controlled execution and provenance capture
- external observability and eval backend integration
- RL-ready export as the downstream handoff boundary

The strongest product distinction remains repo-local agent governance, not self-building another
trace or experiment vendor.

## Current Implementation Baseline

What exists today:

- repository-local agent discovery and publish / unpublish workflow
- worker-backed run execution and run lifecycle tracking
- trajectory and raw trace inspection for run debugging
- dataset creation and reuse across manual runs and eval jobs
- dataset-driven eval fan-out, aggregation, and failure triage
- artifact export for downstream analysis

What is still directional, not shipped:

- LangChain as a full published-agent path
- immutable artifact or image-backed publication
- Docker or Kubernetes runner orchestration
- Phoenix-backed trace and eval observability
- RL-ready export contract beyond the current artifact format

## Strategic Direction

Recommended long-term stack direction:

- keep Agent Atlas as the control plane for repository-local discovery, publish policy, run
  workflow, provenance, and export semantics
- use OpenAI Agents SDK as the current primary runtime path
- add LangGraph-backed execution behind the existing `langchain` framework contract
- standardize telemetry on OpenTelemetry plus OpenInference
- integrate Phoenix as the preferred external observability and evaluation backend
- move publication toward immutable artifacts and images
- introduce runner abstraction with local-process first and Docker next
- treat RL integration phase 1 as offline export first

Why this is the preferred direction:

- it matches the job-to-be-done of integrating external agent scaffolds into internal engineering
  and training workflows
- it preserves Atlas differentiation at the control-plane layer
- it avoids rebuilding a full observability product inside Atlas
- it creates a cleaner handoff to RL and data-processing systems

Primary recommendations by layer:

- control plane: Agent Atlas native product surfaces
- runtime: OpenAI Agents SDK plus LangGraph-backed `langchain`
- telemetry standard: OpenTelemetry plus OpenInference
- observability and eval backend: Phoenix
- artifact layer: immutable build outputs and image references
- runner layer: local-process first, Docker next
- RL link: offline export contract first

## Phase 2 Priorities

### 1. Framework-aware agent integration

Priority: High

Goal:
- make framework handling explicit across discovery, validation, publication, and runtime loading

What this includes:
- introduce a framework registry in the agents stack
- route validation and runtime loading by `manifest.framework`
- formalize `openai-agents-sdk` and `langchain` as the only Phase 2 framework targets
- keep repository-local discovery under `backend/app/agent_plugins/`
- add framework visibility and filtering in the Agents workspace
- surface framework-specific validation issues in discovery results

Acceptance direction:
- a `langchain` plugin can be discovered, published, launched from Playground, and inspected from
  Runs / Trajectory detail

### 2. Immutable artifact and image pipeline

Priority: High

Goal:
- turn publication into a reproducible runtime handoff rather than a logical snapshot only

What this includes:
- define published artifact metadata for each runnable agent
- capture framework, entrypoint, source fingerprint, and build metadata together
- add image or artifact references to the published-agent lifecycle
- expose build status and build provenance in the Agents workspace
- keep one active published artifact per agent in the first phase

Acceptance direction:
- a published agent resolves to a stable runtime artifact or image reference that can be carried
  through execution and export provenance

### 3. Runner orchestration

Priority: High

Goal:
- separate execution control from direct in-process runtime calls

What this includes:
- introduce a runner abstraction with `local-process` first
- add Docker runner support after the abstraction is stable
- carry runner backend and artifact or image metadata into run records
- keep queue and worker internals behind ports so execution infrastructure can evolve without
  rewriting feature logic

Acceptance direction:
- run execution records which runner backend executed the published artifact and preserves that
  provenance through run detail and export

### 4. Phoenix-first observability and eval integration

Priority: High

Goal:
- use Phoenix as the preferred raw trace and eval observability backend while keeping Atlas as the
  control plane

What this includes:
- standardize emitted telemetry on OpenTelemetry plus OpenInference
- export traces and runtime metadata to Phoenix
- add raw trace access patterns in Atlas that are Phoenix-backed or Phoenix-linked
- keep Atlas APIs stable even when the underlying trace backend changes
- avoid direct frontend-to-Phoenix coupling

Acceptance direction:
- a run launched through Atlas can be inspected through Atlas control-plane views and Phoenix-backed
  raw trace workflows without duplicating the same observability product in both places

### 5. RL-ready offline export contract

Priority: High

Goal:
- make exported artifacts directly useful as RL-facing data handoffs

What this includes:
- extend export rows with explicit `eval_job_id`
- extend export rows with explicit `dataset_sample_id`
- preserve published agent snapshot, artifact or image reference, and failure metadata consistently
- include trace-oriented provenance fields such as `prompt_version` and `image_digest`
- keep `POST /api/v1/artifacts/export` backward compatible

Acceptance direction:
- exported rows can be traced back to the originating agent, artifact, dataset, eval job, sample,
  and failure context without extra reconstruction logic

## Supporting Work

### Product and contract clarity

Priority: Medium

Goal:
- keep docs and product language aligned with both shipped behavior and the selected next-stage
  direction

What this includes:
- keep PRD, README, and architecture docs aligned on the control-plane boundary
- document Phoenix as the preferred external observability and eval backend
- avoid documenting Docker / K8s execution as shipped before the runner abstraction exists
- keep public API documentation synchronized with backend contracts

### Frontend control-plane focus

Priority: Medium

Goal:
- keep the frontend focused on Atlas-owned workflows instead of rebuilding full observability
  product surfaces

What this includes:
- show build, runner, provenance, and export state inside Atlas
- add Phoenix-backed summaries and deep links where useful
- keep vendor-specific observability coupling behind backend-owned contracts

## Deferred Tracks

### Kubernetes scheduling

Priority: Medium

Deferred because:
- Docker-backed runner semantics should stabilize before Kubernetes becomes the next carrier

What belongs here later:
- Kubernetes job execution
- image distribution strategy
- cluster-aware operational controls

### Direct RL ingestion

Priority: Medium

Deferred because:
- the first integration goal is an offline RL-ready export contract

What belongs here later:
- direct handoff into internal RL ingestion pipelines
- training-task submission integration
- feedback-loop automation from export to training systems

### Additional agent sources

Priority: Low

Deferred because:
- repository-local discovery is the current stability boundary

What belongs here later:
- external package sources
- remote repository sources
- trust and isolation rules for non-local code

### MCP support

Priority: Low

Deferred because:
- MCP is only represented as a placeholder enum today
- the product still needs a clear artifact and runner story before adding protocol-level support

### Versioned publication

Priority: Low

Deferred because:
- the current next step is immutable runtime handoff, not full release history UX

What belongs here later:
- publish history with rollback semantics
- explicit revision browsing for published agent metadata

### LLM-as-judge evaluation

Priority: Low

Deferred because:
- deterministic scoring still matches the current product stage better
- the current priority is runner, observability, and RL-export quality, not evaluation-model
  complexity
