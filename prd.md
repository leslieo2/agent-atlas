Title: Agent Flight Recorder
Subtitle: A Registered-Agent Workbench for execution, observation, and export

Product Summary
Agent Flight Recorder is a self-hosted workbench for running, observing, and exporting executions of user-registered agents. In v1, the product focuses on OpenAI Agents SDK agents that are already authored by the user and registered into the workbench through a Python registry.
The product is not a new agent framework, and it is not a platform-specific mini-agent wrapper. Its job is to load an existing agent entrypoint, execute it in a reproducible runtime, capture execution records, and make those records usable for debugging and downstream data workflows.

Problem Statement
Teams building agent systems usually face four recurring problems:
Existing agents are hard to connect to a shared experimentation workbench.
Agent runtime environments are difficult to reproduce and maintain across framework versions and dependencies.
Debugging is slow because agent behavior is opaque and execution history is hard to inspect.
Execution data is fragmented, making it difficult to turn real runs into reusable artifacts.
The immediate pain is not a lack of another prompt playground. The immediate pain is that real agents already exist, but they are difficult to plug into a stable run-and-debug workflow.

Target Users
Agent infrastructure engineers
Applied ML and RL engineers
Algorithm teams iterating on agent policies and prompts
Internal platform teams supporting agent experimentation

Primary User in v1
The primary user for v1 is an agent infrastructure engineer who already has a repository-local OpenAI Agents SDK agent and needs to plug it into a shared execution, inspection, and export workflow with minimal integration effort.

Product Goals
Provide a reliable way to run registered OpenAI Agents SDK agents inside the workbench.
Run agents in reproducible local or containerized environments.
Offer trajectory inspection focused on real execution steps and outputs.
Export execution records into reusable JSONL artifacts.
Reduce the integration cost of bringing an existing agent into a shared engineering workflow.

Non-Goals
Building a new general-purpose agent orchestration framework
Building a custom trace database or general APM platform
Supporting every agent framework in the ecosystem in v1
Building a multi-tenant SaaS platform in v1
Replacing existing observability backends such as Phoenix or Langfuse

Why This Fits the JD
The JD implies a platform-oriented role rather than an application-only role. The real engineering need is a system that:
Connects existing agents to internal experimentation and data workflows
Maintains stable and reproducible runtimes
Makes real executions visible and debuggable
Reduces integration cost for new agent implementations
Improves reliability and iteration speed for internal agent systems

Product Scope for v1
v1 should stay narrow enough for a single engineer.

Included:

Registered OpenAI Agents SDK agents
Python registry-based agent catalog
Docker-based or local runner execution
Run dashboard
Playground
Trajectory viewer
JSONL trajectory export

Excluded from v1:

Replay for registered agents
Eval for registered agents
LangChain registered-agent support
MCP registered-agent support
UI-based agent registration
Parquet export as a required v1 capability
Kubernetes-first scheduling
Multi-tenant auth and permissions
A custom tracing backend

Future Phases / Post-v1 Backlog
Replay for registered agents
Batch eval over datasets for registered agents
LangChain and MCP registered-agent support
UI workflows for creating and editing agent registrations
Standardized telemetry pipelines such as OpenTelemetry / OpenInference / Phoenix integration
Parquet export and richer artifact storage

Core User Flows
A. Run an agent
User opens the Playground or Run Dashboard and selects a registered agent.
Control plane creates a run record and schedules a local or Docker runner.
The runner loads the configured Python entrypoint for that agent and executes the real OpenAI Agents SDK agent.
The workbench records run metadata, trajectory steps, and execution records.
The user can open the run workspace to inspect the result.

B. Debug a run
User opens the trajectory viewer for a completed run.
The UI renders a step list or execution timeline based on real recorded execution steps.
User inspects prompt, output, latency, token usage, tool information when present, and errors when present.
User uses the run workspace to understand what happened in the real execution.

C. Export training artifacts
User selects one or more runs.
The exporter converts execution records into JSONL.
Output can feed downstream analysis, dataset curation, or model-training pipelines.

Typical User Workflow in the Current v1 Product
The most common user path in the current product is:
User authors an OpenAI Agents SDK agent inside the repository and registers it in the Python agent registry.
User opens the Playground and selects a registered agent.
User enters a prompt, optionally attaches a dataset, and launches a run.
Backend resolves `agent_id`, loads the registered Python entrypoint, and executes the real agent in a local or Docker runner.
User opens the run workspace to inspect output, trajectory, latency, token usage, and execution metadata.
User exports successful runs as JSONL for downstream analysis or data workflows.

Primary Screens
A. Run Dashboard
Purpose: Search and inspect all executions.
Key elements:
Filters: project, dataset, agent_id, model, tag, time range
Table columns: run_id, agent_id, input summary, status, latency, token cost, tool-call count
Actions: New Run, Export

B. Trajectory Viewer
Purpose: Make real execution understandable.
Key elements:

Step list or execution timeline showing recorded execution steps
Visual state markers for success, failure, latency, and token count
Fast inspection of step-level input, output, and metadata

C. Step Detail Panel
Purpose: Deep inspection per recorded step.
Key elements:

Prompt input and model output
Tool input/output JSON when present
Model metadata and token usage
Error stack when present

D. Playground
Purpose: Manual testing entry point for registered agents.
Key elements:

Registered agent selector
Prompt input
Optional dataset selector
Execution output
Link to the created run workspace

Technical Architecture
A. Frontend Workbench
Next.js + TypeScript
React Flow or equivalent execution visualization for trajectory viewing
Run Dashboard for filtering and inspecting registered-agent runs
Playground for selecting a registered agent and executing it
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
Agent Registry / Agent Catalog for listing available registered agents
Run Orchestrator for scheduling and state transitions
Artifact Exporter for JSONL outputs
Trace and trajectory persistence for execution records captured by the workbench

C. Runtime Layer
Local runner and Docker runner
One execution environment per run
Versioned environments for framework and dependency control
Registered agent entrypoint contract fixed as `build_agent(context) -> Agent`
Only Python modules inside the repository are supported in v1

D. Observability and Storage
Trajectory and execution records captured by the workbench
Run metadata includes agent_id, entrypoint, framework, and resolved_model
SQLite is acceptable for control-plane metadata in v1
Standardized telemetry backends such as Phoenix, OpenTelemetry, and OpenInference are future-phase integrations rather than v1 acceptance requirements

E. Agent / Tool Layer
Registered OpenAI Agents SDK agents
User-authored tools that are part of the registered agent definition
LangChain and MCP support remain post-v1 extensions

Module Responsibilities
Frontend:
Run Dashboard: filter, search, inspect, and export registered-agent runs
Playground: select a registered agent and launch a run
Trajectory Viewer: inspect real execution steps and node relationships when present

Backend:
Agent Registry: load and validate registered agent entrypoints
Run Orchestrator: create runs, resolve agent_id, schedule runners, update states
Runtime Loader: import the configured Python entrypoint and execute the real agent
Artifact Exporter: generate JSONL-ready execution outputs

Infrastructure:
Runner Pool: local and Docker execution with reproducible dependencies
Control-plane persistence: run metadata, datasets, execution records, and exports

Public API and Contracts
`GET /api/v1/agents`
Returns the registered agent catalog for the UI.
Expected response shape:
id
name
description
framework
default_model
tags

`POST /api/v1/runs`
Creates a run from `agent_id`.
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
  "model": "gpt-4.1-mini"
}
```

Required error semantics in v1:
Unknown `agent_id` returns a structured `agent_not_registered` error.
Invalid dataset reference returns a structured `dataset_not_found` error.
Agent entrypoint import or construction failure returns a structured `agent_load_failed` error.
Provider-level failures must remain structured, including at least authentication, missing-model, rate-limit, and timeout cases.

The v1 registered-agent entrypoint contract is:
Only repository-local Python modules may be registered.
Each registered agent must be loadable from the Python registry.
Each registered agent entrypoint must implement `build_agent(context) -> Agent`.

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

v1 Sample Registered Agents
The first test agents should align with three categories derived from official OpenAI Agents SDK examples:
basic
customer_service
tools
These are test objects for validating the registry and runtime path, not separate product features.

Data Model Sketch
Core v1 entities:
registered_agent
run
trajectory_step
dataset
artifact_export

Important normalized fields:

agent_id
entrypoint
framework
resolved_model
run_id
step_id
step_type
input
output
tool_name
latency_ms
token_usage

Non-Functional Requirements and Risks
The system must support both local and Docker execution for registered agents.
All registered agents must be importable from repository-local Python modules without manual runtime patching.
The control plane must fail fast with structured errors when registry configuration, imports, or runtime dependencies are invalid.
The biggest v1 risks are Python dependency drift, container image mismatch, and user-authored tool side effects.

MVP Definition
The product is considered real once this loop works end-to-end:
User selects a registered agent from the UI
Backend creates a run from `agent_id`
Runner loads the configured Python entrypoint and executes the real agent
Workbench captures run, trajectory, and execution metadata
Frontend renders the run workspace and trajectory view
User can export the result as JSONL

v1 Acceptance Criteria
An engineer can register a repository-local OpenAI Agents SDK agent and see it appear in `GET /api/v1/agents` without editing frontend code.
The primary Playground flow can launch a run from `agent_id` and return a run record within 2 seconds, excluding downstream model execution time.
Every successful registered-agent run persists a run record and at least one recorded trajectory step.
The run workspace shows agent_id, resolved_model, status, output, latency, token usage, and trajectory data for every successful run.
JSONL export succeeds for selected registered-agent runs and includes run metadata plus recorded execution steps.
Replay and Eval are not exposed as supported actions for newly created registered-agent runs.

Success Metrics
Time to connect an existing repository-local OpenAI Agents SDK agent to the workbench: under 30 minutes for an engineer familiar with the codebase.
Time to inspect a completed execution in the run workspace: under 5 minutes from run completion to finding prompt, output, latency, token usage, and trajectory details.
Run creation acknowledgment latency: p95 under 2 seconds for the control-plane request path, excluding model execution time.
Percentage of successful registered-agent runs exportable as JSONL artifacts: 100%.
Time to add a new registered agent entry to the Python registry: under 10 minutes once the agent module already exists.

Product Positioning
Agent Flight Recorder is not a chatbot product and not a new agent framework. It is an engineering workbench for registering, running, inspecting, and exporting real agent executions.
The simplest positioning line is:
A self-hosted registered-agent workbench that executes existing OpenAI Agents SDK agents, captures execution records, and turns them into reusable engineering artifacts.
