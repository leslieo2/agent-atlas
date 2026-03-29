# Agent Atlas PRD

## Subtitle
Repository-local agent control plane for RL-ready execution data

## Product Summary
Agent Atlas is a self-hosted control plane for teams that need to turn repository-local agents into
governed runtime assets.

Its job is not to replace an observability vendor and not to become a general-purpose agent
framework. Its job is to:

- discover repository-local agent implementations
- validate and publish runnable agent definitions
- build and track immutable runtime artifacts over time
- orchestrate controlled execution through runner backends
- preserve run, eval, and artifact provenance
- export RL-ready execution data for downstream training systems

The current repository already implements a local-first workbench across Agents, Runs, Playground,
Datasets, Evals, and Trajectory detail. The next product stage keeps that control plane and shifts
trace and eval observability toward a Phoenix-first backend strategy.

## Business Value
Agent Atlas creates business value by turning codebase-local agents into controlled engineering
assets that can be:

- connected to a shared execution system without ad hoc platform edits
- observed and evaluated through a standard telemetry path
- reproduced through published snapshots and runtime artifacts
- exported as training-ready records with explicit provenance

In DeepSeek-style infrastructure terms, Agent Atlas is the layer that links external agent
scaffolds, internal execution infrastructure, and RL-facing data production.

## Problem Statement
Teams building agents usually hit the same operational gaps:

- external agent frameworks are easy to prototype with but hard to integrate into a shared control
  plane
- prompt, tool, trace, eval, and failure data drift across notebooks, dashboards, and local scripts
- agent definitions are not governed as first-class engineering assets
- runtime reproducibility is weak because source code, dependencies, and execution environments are
  not tied together tightly enough
- RL and training teams often receive partial exports instead of stable, provenance-rich data
  contracts

The immediate need is not another chat UI. The immediate need is a control plane that takes
repository-local agents through discovery, publication, execution, observability, evaluation, and
RL-ready export.

## Target Users
- agent infrastructure engineers
- applied ML and RL engineers
- platform engineers supporting agent experimentation
- algorithm teams iterating on prompts, tools, and evaluation loops

## Primary User
The primary user is an agent infrastructure engineer who owns repository-local integrations and
needs a reliable publish, run, debug, evaluate, and export loop with low setup overhead.

## Product Goals
- make repository-local agent scaffolds discoverable and publishable through a stable contract
- keep runnable exposure explicit so draft or invalid agents do not leak into execution systems
- support framework-aware execution across a small set of formal runtime targets
- move runtime execution toward immutable artifacts and isolated runners
- integrate external observability and evaluation backends without losing Atlas control-plane
  ownership
- export RL-ready execution records with enough provenance to be consumed offline by training teams

## Current Product Baseline
The current product baseline is the implemented repository state, not the target architecture.

### Implemented product surfaces
- Agents workspace for discovery, validation, publish, and unpublish
- Run dashboard for filtering, selection, and artifact export
- Trajectory viewer for graph inspection, step inspection, and comparable-run diffing
- Playground for direct manual runs and trace refresh
- Datasets workspace for JSONL upload and manual sample creation
- Eval workbench for dataset-driven batch jobs, failure clustering, and sample drill-down

### Implemented backend capabilities
- repository-local agent discovery from `backend/app/agent_plugins/`
- publish and unpublish workflow for runnable agents
- SQLite-backed run, trace, trajectory, dataset, eval, artifact, and task persistence
- worker-backed run execution queue
- eval fan-out into child runs plus aggregation into eval job results
- trace ingestion and trace normalization endpoints
- JSONL artifact export
- parquet artifact export with JSON fallback when optional parquet dependencies are unavailable

### Current runtime facts that must stay accurate
- published OpenAI Agents SDK plugins are the current first-class published runtime path
- `manifest.framework` already exists in agent metadata and `AdapterKind` includes
  `openai-agents-sdk`, `langchain`, and `mcp`
- LangChain currently exists as runtime groundwork, not as a fully productized published-agent
  discovery and execution path
- MCP is only a placeholder in current shared enums and traces; it is not a supported published
  protocol
- the current implementation does not expose a real Docker or Kubernetes runner carrier
  abstraction through config and wiring, so containerized execution must not be documented as a
  shipped capability
- Phoenix is not yet the active backend for the current codebase; it is the preferred next-stage
  observability and eval backend

## Product Boundary
### Agent Atlas owns
- repository-local discovery and validation
- publish and unpublish control
- runnable catalog and framework-aware integration contracts
- run submission, execution control, and runner selection
- artifact and image provenance
- dataset and eval job linkage
- RL-ready export contracts

### External backends own
- raw span storage and trace exploration
- prompt and experiment-oriented observability workflows
- vendor-specific evaluator tooling

Phoenix is the preferred first external backend for the observability and evaluation side of that
boundary.

## Current Scope
### Included in the current product
- repository-local agent discovery and publish flow
- published runnable agent catalog
- manual runs from Playground
- run history, filtering, and run detail inspection
- trajectory graph and step inspection
- raw trace retrieval for runs
- dataset creation and upload
- eval job creation and sample result inspection
- JSONL export and parquet fallback export

### Explicitly not current capability
- immutable build artifacts or image-backed publication
- Docker or Kubernetes runner orchestration
- Phoenix-backed trace or eval storage
- direct RL job submission
- remote repository, external package, or worktree-external agent sources
- MCP protocol support as a runnable published-agent path
- versioned publish artifacts with rollback semantics
- LLM-as-judge evaluation
- a dedicated multi-tenant auth and permissions model

## Next-Stage Product Direction
The next stage of Agent Atlas shifts from a local-first workbench to a control plane for RL-ready
data production.

### Directional pillars
- framework-aware agent integration
- immutable artifact and image pipeline
- runner orchestration with local-process first and Docker next
- Phoenix-first observability and eval backend integration
- RL-ready offline export contract

### Why this direction
- it aligns the product with real agent infrastructure work instead of a generic workbench story
- it preserves the strongest Atlas differentiation: repository-local agent governance
- it avoids rebuilding a full observability vendor inside Atlas
- it makes exported run data usable by training teams without manual reconstruction

## Core User Flows
### A. Connect a repository-local agent scaffold
1. A developer adds or updates a plugin under `backend/app/agent_plugins/`.
2. Atlas discovers the module, reads `AGENT_MANIFEST`, validates the build contract, and shows
   validation state in the Agents workspace.
3. The user publishes a valid agent.
4. The published agent becomes eligible for execution and downstream data generation.

### B. Launch a controlled run
1. The user opens Playground and selects a published agent.
2. The user enters a prompt and optionally associates a dataset and tags.
3. The backend creates a queued run and submits it to the worker queue.
4. The execution path resolves the published agent snapshot and, in the next stage, the selected
   artifact or image.
5. The user opens run detail to inspect status, provenance, trajectory, and trace links.

### C. Run a dataset evaluation
1. The user creates or uploads a dataset.
2. The user opens Evals, selects a published agent and dataset, and creates an eval job.
3. The backend fans the dataset out into child runs and schedules aggregation.
4. The UI shows pass rate, failure clusters, and sample-level outcomes.
5. The user pivots from failed samples into run detail or downstream export.

### D. Inspect trace and failure data
1. The user opens a run detail page.
2. Atlas renders projected trajectory steps and run metadata.
3. The user inspects raw spans, either in Atlas summaries or through Phoenix-backed deep links in
   the next stage.
4. The user uses that context to debug failures or compare candidates.

### E. Export RL-ready data
1. The user exports selected runs from the dashboard, run detail view, or failure selection in
   Evals.
2. The exporter emits JSONL or parquet-compatible records.
3. The exported rows include enough run, eval, agent, and trace provenance to be consumed offline
   by RL or data-processing systems.

## Primary Screens
### Agents
Purpose: discover, validate, publish, and inspect repository-local plugins.

Key elements:
- grouped sections for published, published with draft changes, draft, and invalid agents
- framework, entrypoint, model, tag, and validation metadata
- publish and unpublish actions
- future build and artifact status

### Runs
Purpose: search, filter, export, and open individual run detail views.

Key elements:
- filters for project, dataset, agent, model, status, tag, and time range
- run table with execution context and status
- artifact export actions
- future artifact and runner provenance

### Trajectory Detail
Purpose: inspect projected execution structure and run metadata.

Key elements:
- trajectory graph
- step inspector
- comparable-run selection and diff summary
- run metadata including resolved model, entrypoint, runtime backend, and failure fields
- future Phoenix-backed raw trace access

### Playground
Purpose: launch direct manual runs against published agents.

Key elements:
- published agent selector
- optional dataset selection
- prompt input and tags
- latest run tracking
- future artifact and runner metadata

### Datasets
Purpose: prepare reusable sample sets for evals and manual runs.

Key elements:
- JSONL upload
- manual single-sample dataset creation
- preview of imported samples
- deep links into Playground and Evals

### Evals
Purpose: batch fan-out dataset rows into runs and inspect aggregated quality signals.

Key elements:
- eval job creation form
- recent eval jobs list
- summary metrics and failure distribution
- sample-level table with direct links into run detail
- selective export of failed runs
- future candidate-vs-baseline comparison

## Technical Architecture
### Frontend
- Next.js App Router
- layered product architecture: `app -> widgets -> features -> entities -> shared`
- TanStack Query for server state
- trajectory rendering via React Flow
- backend remains the integration boundary for external observability backends

### Backend
- FastAPI modular monolith
- thin route layer under `backend/app/api/routes`
- feature modules under `backend/app/modules`
- infrastructure adapters and repositories under `backend/app/infrastructure`
- composition root under `backend/app/bootstrap`

### Current execution model
- `POST /api/v1/runs` creates a queued run immediately
- a background worker claims queued tasks and executes runs
- eval jobs enqueue both execution and aggregation tasks
- trajectory steps are projected from traces and persisted
- run detail combines stored run metadata with trajectory and trace data

### Target execution direction
- publication resolves to a stable snapshot and then to an immutable artifact or image
- runner backends execute the resolved artifact in a controlled environment
- telemetry is standardized on OpenTelemetry plus OpenInference
- Phoenix receives raw runtime spans and experiment-oriented evaluation data
- Atlas remains the source of truth for control-plane state and export provenance

### Storage
- SQLite-backed local persistence is the current default control-plane store
- persisted entities include published agents, runs, trajectory steps, trace spans, datasets, eval
  jobs, eval sample results, artifacts, and queued tasks
- in the next stage, local control-plane persistence remains in Atlas even when raw trace and eval
  observability move to Phoenix

## Public API and Contracts
### Stable current APIs
- Agents:
  - `GET /api/v1/agents`
  - `GET /api/v1/agents/discovered`
  - `POST /api/v1/agents/{agent_id}/publish`
  - `POST /api/v1/agents/{agent_id}/unpublish`
- Runs:
  - `GET /api/v1/runs`
  - `POST /api/v1/runs`
  - `GET /api/v1/runs/{run_id}`
  - `POST /api/v1/runs/{run_id}/terminate`
  - `GET /api/v1/runs/{run_id}/trajectory`
  - `GET /api/v1/runs/{run_id}/traces`
- Datasets:
  - `GET /api/v1/datasets`
  - `POST /api/v1/datasets`
- Evals:
  - `POST /api/v1/eval-jobs`
  - `GET /api/v1/eval-jobs`
  - `GET /api/v1/eval-jobs/{eval_job_id}`
  - `GET /api/v1/eval-jobs/{eval_job_id}/samples`
- Artifacts:
  - `GET /api/v1/artifacts`
  - `POST /api/v1/artifacts/export`
  - `GET /api/v1/artifacts/{artifact_id}`
- Traces:
  - `POST /api/v1/traces/normalize`
  - `POST /api/v1/traces/ingest`

### Planned additions
- optional trace filters on `GET /api/v1/runs/{run_id}/traces`
- eval comparison endpoint for candidate-vs-baseline analysis
- additional run and artifact provenance fields for artifact/image references and RL-ready export

## Repository-Local Agent Contract
Current contract:
- modules live under `backend/app/agent_plugins/`
- each module exposes `AGENT_MANIFEST`
- each module exposes `build_agent(context)`

Direction:
- the contract remains repository-local
- `manifest.framework` becomes the dispatch key for validation, publication, runtime loading, and
  later artifact building
- the initial formal framework set remains `openai-agents-sdk` and `langchain`

## External Observability and Eval Contract
Direction:
- Atlas does not expose Phoenix directly to users as the control plane
- Atlas emits standardized telemetry and queries or links Phoenix-backed observability data
- Phoenix is the preferred first backend for raw spans, experiments, and prompt-oriented debugging

## RL Export Contract
Current export semantics:
- exported rows include run, step, message, reward, and published-agent summary fields

Next-stage export semantics:
- exported rows must additionally preserve agent snapshot, artifact or image reference, eval job id,
  dataset sample id, failure fields, prompt version, image digest, and trace identifiers
- phase 1 remains offline export first, not direct RL job submission

## Non-Goals
- building a new general-purpose agent framework
- replacing Phoenix or another observability backend with a home-grown equivalent
- becoming a hosted SaaS control plane
- supporting every framework in the ecosystem in the current phase
- acting as a code authoring IDE for agent source files
- shipping direct RL training orchestration in the first integration stage

## Acceptance Criteria For The Next Stage
- a valid repository-local `langchain` or `openai-agents-sdk` agent can be published through the
  same Atlas workflow
- run execution preserves explicit published-agent and artifact provenance
- Phoenix can receive and expose run traces without becoming the source of truth for Atlas control
  state
- eval jobs remain linked to datasets, runs, and exported artifacts
- offline exports are sufficient for RL-facing downstream consumption without ad hoc join logic

## Product Positioning
Agent Atlas is not a chatbot product and not an observability vendor. It is a repository-local
agent control plane that governs how agents enter execution systems and how their outputs become
reproducible, observable, evaluable, and RL-ready engineering assets.

### Positioning sentence
> A self-hosted control plane that turns repository-local agents into governed runtime assets and
> RL-ready execution data.
