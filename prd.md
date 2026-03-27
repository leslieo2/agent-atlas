Title: Agent Flight Recorder
Subtitle: A Scanned-and-Published Agent Workbench for execution, observation, and export

Product Summary
Agent Flight Recorder is a self-hosted workbench for discovering, publishing, running, observing, and exporting executions of user-authored agents. In v1, the product focuses on OpenAI Agents SDK agents that live inside the repository and follow a product-defined plugin contract. The workbench automatically discovers those agents, validates that they satisfy the contract, lets users explicitly publish them, and only allows published and currently valid agents to be run from the UI.
The product is not a new agent framework, and it is not a generic plugin marketplace. Its job is to load an existing repository-local agent entrypoint, execute it in a reproducible runtime, capture execution records, and make those records usable for debugging and downstream data workflows.

Problem Statement
Teams building agent systems usually face five recurring problems:
Existing agents are hard to connect to a shared experimentation workbench.
Agent runtime environments are difficult to reproduce and maintain across framework versions and dependencies.
Debugging is slow because agent behavior is opaque and execution history is hard to inspect.
Execution data is fragmented, making it difficult to turn real runs into reusable artifacts.
The integration path for a new agent is usually operationally messy because discovery, validation, and publication are not part of the product workflow.
The immediate pain is not a lack of another prompt playground. The immediate pain is that real agents already exist, but they are difficult to connect to a stable run-and-debug workflow without platform engineers hand-editing internal control-plane wiring.

Target Users
Agent infrastructure engineers
Applied ML and RL engineers
Algorithm teams iterating on agent policies and prompts
Internal platform teams supporting agent experimentation

Primary User in v1
The primary user for v1 is an agent infrastructure engineer who already has a repository-local OpenAI Agents SDK agent and needs to plug it into a shared execution, inspection, and export workflow with minimal integration effort and clear publication control.

Product Goals
Provide a reliable way to discover repository-local OpenAI Agents SDK agents inside the workbench.
Make agent publication an explicit control-plane action rather than a backend-only code edit.
Run published OpenAI Agents SDK agents in reproducible local or containerized environments.
Offer trajectory inspection focused on real execution steps and outputs.
Export execution records into reusable JSONL artifacts.
Reduce the integration cost of bringing an existing agent into a shared engineering workflow.

Non-Goals
Building a new general-purpose agent orchestration framework
Building a custom trace database or general APM platform
Supporting every agent framework in the ecosystem in v1
Building a multi-tenant SaaS platform in v1
Replacing existing observability backends such as Phoenix or Langfuse
Supporting worktree-external paths, pip packages, or remote agent sources in v1
Freezing published agent source code into versioned runtime snapshots in v1

Why This Fits the JD
The JD implies a platform-oriented role rather than an application-only role. The real engineering need is a system that:
Connects existing agents to internal experimentation and data workflows
Maintains stable and reproducible runtimes
Makes real executions visible and debuggable
Reduces integration cost for new agent implementations
Adds publication controls so draft or broken agents do not leak into the shared UI
Improves reliability and iteration speed for internal agent systems

Product Scope for v1
v1 should stay narrow enough for a single engineer.

Included:

Repository-local OpenAI Agents SDK agent plugins
Automatic discovery of agent plugins from `backend/app/agent_plugins/`
Contract validation for discovered plugins
Explicit publish / unpublish workflow
Published runnable agent catalog
Local and Docker runner execution
Agent management workspace
Run dashboard
Playground
Trajectory viewer
JSONL trajectory export

Excluded from v1:

Replay for published agents
Eval for published agents
LangChain agent-plugin support
MCP agent-plugin support
UI-based authoring of agent source code
Parquet export as a required v1 capability
Kubernetes-first scheduling
Multi-tenant auth and permissions
A custom tracing backend
Versioned publish artifacts or frozen source bundles
External package, worktree-external, or remote agent sources

Future Phases / Post-v1 Backlog
Replay for published agents
Batch eval over datasets for published agents
Versioned publish snapshots for agent source and manifest
Support for external package sources after repository-local plugins are stable
LangChain and MCP plugin contracts
Standardized telemetry pipelines such as OpenTelemetry / OpenInference / Phoenix integration
Parquet export and richer artifact storage

Core User Flows
A. Discover and publish an agent
User authors an OpenAI Agents SDK plugin module inside `backend/app/agent_plugins/`.
The control plane discovers the module, derives its entrypoint, reads its manifest, and validates that it satisfies the product contract.
The Agent Management workspace shows the plugin as Draft or Invalid.
The user reviews metadata and validation results, then explicitly publishes a valid plugin.
The published agent becomes visible in the runnable catalog and in the Playground selector.

B. Run an agent
User opens the Playground or Run Dashboard and selects a published agent.
Control plane creates a run record and schedules a local or Docker runner.
The runtime resolves the published agent snapshot, loads the configured Python entrypoint, and executes the real OpenAI Agents SDK agent.
The workbench records run metadata, trajectory steps, and execution records.
The user can open the run workspace to inspect the result.

C. Debug a run
User opens the trajectory viewer for a completed run.
The UI renders a step list or execution timeline based on real recorded execution steps.
User inspects prompt, output, latency, token usage, tool information when present, and errors when present.
User uses the run workspace to understand what happened in the real execution.

D. Export training artifacts
User selects one or more runs.
The exporter converts execution records into JSONL.
Output can feed downstream analysis, dataset curation, or model-training pipelines.

Typical User Workflow in the Current v1 Product
The most common user path in the current product is:
User authors an OpenAI Agents SDK plugin inside `backend/app/agent_plugins/`.
User opens the Agent Management workspace and sees the plugin appear as Draft or Invalid based on validation.
User publishes a valid plugin.
User opens the Playground and selects the published agent.
User enters a prompt, optionally attaches a dataset, and launches a run.
Backend resolves `agent_id` from the runnable catalog, loads the published Python entrypoint, and executes the real agent in a local or Docker runner.
User opens the run workspace to inspect output, trajectory, latency, token usage, and execution metadata.
User exports successful runs as JSONL for downstream analysis or data workflows.

Primary Screens
A. Agent Management
Purpose: Discover, validate, publish, and unpublish repository-local agent plugins.
Key elements:
Groups: Published, Draft, Invalid
Agent cards: name, agent_id, description, default model, tags, entrypoint
Status surfaces: publish_state, validation_status, validation_issues
Actions: Publish, Unpublish, Open in Playground

B. Run Dashboard
Purpose: Search and inspect all executions.
Key elements:
Filters: project, dataset, agent_id, model, tag, time range
Table columns: run_id, agent_id, input summary, status, latency, token cost, tool-call count
Actions: New Run, Export

C. Trajectory Viewer
Purpose: Make real execution understandable.
Key elements:
Step list or execution timeline showing recorded execution steps
Visual state markers for success, failure, latency, and token count
Fast inspection of step-level input, output, and metadata

D. Step Detail Panel
Purpose: Deep inspection per recorded step.
Key elements:
Prompt input and model output
Tool input/output JSON when present
Model metadata and token usage
Error stack when present

E. Playground
Purpose: Manual testing entry point for published agents.
Key elements:
Published agent selector
Prompt input
Optional dataset selector
Execution output
Link to the created run workspace

Technical Architecture
A. Frontend Workbench
Next.js + TypeScript
React Flow or equivalent execution visualization for trajectory viewing
Agent Management workspace for discovery, validation, and publication
Run Dashboard for filtering and inspecting published-agent runs
Playground for selecting a published agent and executing it
Trajectory workspace for step inspection and timeline viewing
Implementation layering in the frontend follows:
App Router for route entrypoints and layout
Widget layer for workspace-level orchestration
Feature layer for focused user capabilities
Entity layer for typed API mapping and domain presentation helpers
Shared layer for low-level UI and generic utilities
Detailed frontend rules live in `frontend/ARCHITECTURE.md`.

B. Control Plane API
FastAPI
Agent Discovery API for listing discovered plugins and their validation state
Published Agent Catalog API for listing runnable agents
Agent Publication API for publish and unpublish actions
Run Orchestrator for scheduling and state transitions
Artifact Exporter for JSONL outputs
Trace and trajectory persistence for execution records captured by the workbench

C. Runtime Layer
Local runner and Docker runner
One execution environment per run
Versioned environments for framework and dependency control
Published agent runtime loading driven by the published catalog rather than the discovery view
Agent plugin contract fixed as `AGENT_MANIFEST` plus `build_agent(context) -> Agent`
Only Python modules inside `backend/app/agent_plugins/` are supported in v1

D. Observability and Storage
Trajectory and execution records captured by the workbench
Run metadata includes agent_id, entrypoint, framework, and resolved_model
Published agent metadata persists manifest and entrypoint snapshots for audit and run creation
SQLite is acceptable for control-plane metadata in v1
Standardized telemetry backends such as Phoenix, OpenTelemetry, and OpenInference are future-phase integrations rather than v1 acceptance requirements

E. Agent / Tool Layer
Published OpenAI Agents SDK agents
User-authored tools that are part of the published agent definition
LangChain and MCP support remain post-v1 extensions

Hexagonal Architecture Constraints
The backend must continue to follow Hexagonal Architecture.
The `agents` feature owns the agent plugin contract, discovery queries, publication commands, and runnable catalog ports.
The `runs` feature only depends on a published runnable catalog and runtime port. It must not know how filesystem scanning, module import, SDK validation, or publication persistence work.
Infrastructure is responsible for filesystem scanning, module import, OpenAI Agents SDK `Agent` validation, and persistence of published agent records.
The composition root assembles discovery, publication, runnable catalog, and runtime loading implementations. Application and domain layers must not directly import concrete infrastructure modules or the SDK package.

Module Responsibilities
Frontend:
Agent Management: discover, validate, publish, and unpublish agent plugins
Run Dashboard: filter, search, inspect, and export published-agent runs
Playground: select a published agent and launch a run
Trajectory Viewer: inspect real execution steps and node relationships when present

Backend:
Agents: discover plugins, validate manifests and entrypoints, manage publish state, expose runnable catalog
Run Orchestrator: create runs, resolve agent_id from the runnable catalog, schedule runners, update states
Runtime Loader: load the published Python entrypoint and execute the real agent
Artifact Exporter: generate JSONL-ready execution outputs

Infrastructure:
Filesystem scanner: enumerate repository-local plugin modules under `backend/app/agent_plugins/`
Published-agent persistence: store publish records and agent snapshots
Runner Pool: local and Docker execution with reproducible dependencies
Control-plane persistence: run metadata, datasets, execution records, and exports

Public API and Contracts
`GET /api/v1/agents`
Returns the published runnable agent catalog for the UI.
Expected response shape:
agent_id
name
description
framework
entrypoint
default_model
tags

`GET /api/v1/agents/discovered`
Returns all discovered repository-local plugins, including draft and invalid items.
Expected response shape extends runnable metadata with:
publish_state
validation_status
validation_issues

`POST /api/v1/agents/{agent_id}/publish`
Publishes a discovered plugin if and only if the plugin passes validation at request time.
The published record must save a snapshot of:
agent_id
entrypoint
framework
default_model
tags

`POST /api/v1/agents/{agent_id}/unpublish`
Removes an agent from the runnable catalog but does not delete the underlying source module.

`POST /api/v1/runs`
Creates a run from a published and currently valid `agent_id`.
Required v1 inputs:
project
agent_id
input_summary
prompt
Optional v1 inputs:
dataset
tags
project_metadata

Run metadata must record:
agent_id
entrypoint
framework
resolved_model
agent_snapshot

Example `POST /api/v1/runs` request:
```json
{
  "project": "support-workbench",
  "agent_id": "customer_service",
  "input_summary": "Refund request for delayed shipment",
  "prompt": "Customer says the package is delayed and asks for a refund. Respond with the next action.",
  "dataset": "support-inbox-v1",
  "tags": ["playground", "refund"]
}
```

Example successful run response:
```json
{
  "run_id": "generated-run-id",
  "agent_id": "customer_service",
  "status": "queued",
  "project": "support-workbench",
  "dataset": "support-inbox-v1",
  "model": "gpt-5.4-mini"
}
```

Required error semantics in v1:
Unknown or unpublished `agent_id` returns a structured `agent_not_published` error.
Discovered but invalid agent publish attempts return a structured `agent_validation_failed` error.
Agent entrypoint import or construction failure at runtime returns a structured `agent_load_failed` error.
Provider-level failures must remain structured, including at least authentication, missing-model, rate-limit, and timeout cases.

The v1 agent plugin contract is:
Only repository-local Python modules inside `backend/app/agent_plugins/` may be discovered.
The system derives `entrypoint` from the Python module path and the fixed `build_agent` symbol.
Each plugin module must export `AGENT_MANIFEST`.
Each plugin module must implement `build_agent(context) -> Agent`.
`AGENT_MANIFEST` must contain:
agent_id
name
description
default_model
tags
framework is fixed to `openai-agents-sdk` by the platform rather than author-configurable.

Dataset Semantics in v1
In the current product, a dataset is a named collection of standardized task samples associated with a business scenario or evaluation context.
A dataset typically contains:
input samples that represent real tasks or prompts
optional expected outputs or reference answers
optional tags that classify scenario, difficulty, or task type

The dataset serves three purposes in v1:
It gives a run business context, so the execution is tied to a known task set rather than treated as an isolated prompt experiment.
It provides a stable anchor for future comparison, replay, evaluation, and export workflows.
It makes repeated experimentation more structured by grouping runs under a reusable sample set.

In the Playground, dataset selection is optional. Selecting a dataset associates the run with that named sample set and its context. It does not imply that the full dataset is batch-executed inside the Playground.

v1 Sample Agent Plugins
The first test agents should align with three categories derived from official OpenAI Agents SDK examples:
basic
customer_service
tools
These are test objects for validating the discovery, publication, and runtime paths, not separate product features.

Data Model Sketch
Core v1 entities:
discovered_agent
published_agent
run
trajectory_step
dataset
artifact_export

Important normalized fields:
agent_id
entrypoint
framework
default_model
resolved_model
publish_state
validation_status
validation_issues
run_id
step_id
step_type
input
output
tool_name
latency_ms
token_usage

Non-Functional Requirements and Risks
The system must support both local and Docker execution for published agents.
All repository-local agent plugins must be discoverable from `backend/app/agent_plugins/` without manual runtime patching.
The control plane must fail fast with structured errors when plugin manifests, imports, or runtime dependencies are invalid.
Published agents that later become invalid must disappear from the runnable catalog and Playground, but remain visible in discovery surfaces as `published + invalid`.
The biggest v1 risks are Python dependency drift, container image mismatch, and user-authored tool side effects.

MVP Definition
The product is considered real once this loop works end-to-end:
User adds a repository-local OpenAI Agents SDK plugin
Workbench discovers it and shows validation results
User publishes the plugin
Backend creates a run from a published `agent_id`
Runner loads the published Python entrypoint and executes the real agent
Workbench captures run, trajectory, and execution metadata
Frontend renders the run workspace and trajectory view
User can export the result as JSONL

v1 Acceptance Criteria
An engineer can add a repository-local OpenAI Agents SDK plugin and see it appear in `GET /api/v1/agents/discovered` without editing frontend code.
A valid discovered plugin can be published and then appears in `GET /api/v1/agents`.
The primary Playground flow can launch a run from a published `agent_id` and return a run record within 2 seconds, excluding downstream model execution time.
Every successful published-agent run persists a run record and at least one recorded trajectory step.
The run workspace shows agent_id, resolved_model, status, output, latency, token usage, and trajectory data for every successful run.
JSONL export succeeds for selected published-agent runs and includes run metadata plus recorded execution steps.
Replay and Eval are not exposed as supported actions for newly created published-agent runs.
If a published agent later fails validation, it disappears from `GET /api/v1/agents` and the Playground, while remaining visible in discovery surfaces with its validation issues.

Success Metrics
Time to connect an existing repository-local OpenAI Agents SDK plugin to the workbench: under 30 minutes for an engineer familiar with the codebase.
Time to make a new valid plugin visible as Draft in the Agent Management workspace: under 5 minutes once the module exists.
Time to publish a valid plugin and make it runnable from Playground: under 10 minutes once the module exists.
Time to inspect a completed execution in the run workspace: under 5 minutes from run completion to finding prompt, output, latency, token usage, and trajectory details.
Run creation acknowledgment latency: p95 under 2 seconds for the control-plane request path, excluding model execution time.
Percentage of successful published-agent runs exportable as JSONL artifacts: 100%.

Product Positioning
Agent Flight Recorder is not a chatbot product and not a new agent framework. It is an engineering workbench for discovering, publishing, running, inspecting, and exporting real agent executions.
The simplest positioning line is:
A self-hosted workbench that discovers repository-local OpenAI Agents SDK agents, publishes runnable ones, captures execution records, and turns them into reusable engineering artifacts.
