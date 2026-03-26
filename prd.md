English PRD draft based on the Agent Infrastructure Engineer JD and the product discussion.

Title: Agent Flight Recorder
Subtitle: An Agent Infra Workbench for replay, evaluation, and RL-ready trajectory export

Product Summary
Agent Flight Recorder is a self-hosted workbench for running, observing, replaying, and evaluating agent executions. It integrates external agent scaffolds such as OpenAI Agents SDK, LangChain, and MCP-based tools into a unified, containerized runtime, then converts execution traces into reusable assets for debugging, benchmarking, and downstream RL or SFT pipelines.
The product is not a new agent framework. It is an engineering platform focused on unified execution, unified observability, and unified export.

Problem Statement
Teams building agent systems usually face four recurring problems:
External agent scaffolds are hard to connect to internal training and evaluation pipelines.
Agent runtime environments are difficult to reproduce and maintain across framework versions and dependencies.
Debugging is slow because agent behavior is opaque and traces are hard to inspect or replay.
Execution data is fragmented, making it difficult to turn production runs into evaluation datasets or training artifacts.
Target Users
Agent infrastructure engineers
Applied ML and RL engineers
Algorithm teams iterating on agent policies and prompts
Internal platform teams supporting agent experimentation
Product Goals
Provide a unified adapter layer for mainstream agent scaffolds.
Run agents in reproducible containerized environments.
Offer trajectory visualization, step-level debugging, and step replay.
Support lightweight evaluation workflows over datasets and benchmark suites.
Export trajectories into RL-, SFT-, or preference-ready formats.
Non-Goals
Building a new general-purpose agent orchestration framework
Building a custom trace database or general APM platform
Supporting every agent framework in the ecosystem
Building a multi-tenant SaaS platform in v1
Replacing existing observability backends such as Phoenix or Langfuse
Why This Fits the JD
The JD implies a platform-oriented role rather than an application-only role. The real engineering need is a system that:
Connects external agent tooling to internal RL infrastructure
Maintains stable containerized runtimes
Makes trajectories visible and debuggable
Reduces integration cost for new agent scaffolds
Improves reliability and scalability of internal agent systems
Product Scope for v1
v1 should stay narrow enough for a single engineer.
Included:

OpenAI Agents SDK adapter
LangChain adapter
MCP tool integration shim
Docker-based isolated runner per execution
Run dashboard
Trajectory viewer
Step detail panel
Step replay with diff
Batch evaluation over a dataset
JSONL and Parquet trajectory export
Excluded from v1:

Kubernetes-first scheduling
Multi-tenant auth and permissions
A custom tracing backend
Broad support for many frameworks beyond the first two
Core User Flows
A. Run an agent
User starts a run from the UI.
Control plane creates a run record and schedules a runner.
The agent executes inside a Docker image with pinned dependencies.
Execution emits traces through OpenTelemetry / OpenInference.
Traces are indexed and visible in the workbench.
B. Debug a run

User opens the trajectory viewer.
The UI renders a step graph of LLM calls, tool calls, planner steps, and memory events.
User clicks a node to inspect prompt, tool input/output, latency, token usage, and errors.
User compares the step with a previous run through a diff panel.
C. Replay a step

User selects a failed or suspicious step.
User edits prompt text, model choice, or tool parameters.
The system replays that step in isolation.
The UI returns the new output and a structured diff against the original.
User can save the replay as a new run or candidate configuration.
D. Evaluate a dataset

User uploads or selects a dataset in JSONL.
User launches batch evaluation.
The system replays runs across samples and computes metrics.
User drills into failures by opening the corresponding trajectories.
E. Export training artifacts

User selects runs or eval results.
The exporter converts execution traces into JSONL or Parquet.
Output can feed SFT, preference modeling, or reward-model workflows.
Primary Screens
A. Run Dashboard
Purpose: Search and inspect all executions.
Key elements:
Filters: project, dataset, model, tag, time range
Table columns: run_id, input summary, status, latency, token cost, tool-call count
Actions: New Run, Batch Eval
B. Trajectory Viewer
Purpose: Make agent execution understandable.
Key elements:

DAG or step graph showing LLM calls, tools, planner steps, memory writes
Visual state markers for success, failure, latency, and token count
Step-level expand/collapse for fast inspection
C. Step Detail Panel
Purpose: Deep inspection per node.
Key elements:

Prompt input and model output
Tool input/output JSON
Model metadata, temperature, token usage
Error stack when present
Diff versus previous run
D. Step Replay Panel
Purpose: Fast iteration without rerunning the full workflow.
Key elements:

Editable prompt
Model switcher
Tool parameter editor
Replay action
Structured result diff
E. Eval Bench
Purpose: Compare runs over a dataset.
Key elements:

Dataset browser
Run comparison table
Metrics: success rate, tool success rate, latency, token usage, judge score
Drill-down into failing samples and their trajectories
F. Playground
Purpose: Manual testing entry point.
Key elements:

Prompt input
Agent type selector: OpenAI Agents SDK or LangChain
Tool selection
Model selection
Real-time execution output and trace link
Technical Architecture
A. Frontend Workbench
Next.js + TypeScript
React Flow for trajectory graphs
Monaco Diff Editor for prompt/output comparison
TanStack Table for run and eval tables
Implementation layering in the frontend follows:
App Router for route entrypoints and layout
Widget layer for workspace-level orchestration
Feature layer for focused user capabilities
Entity layer for typed API mapping and domain presentation helpers
Shared layer for low-level UI and generic utilities
Detailed frontend rules live in `frontend/ARCHITECTURE.md`.
B. Control Plane API

FastAPI
Run Orchestrator for scheduling and state transitions
Eval Service for batch execution and scoring
Replay Service for step-level reruns
Adapter Manager for schema normalization
Trace Gateway for OTLP ingestion and run/span indexing
Artifact Exporter for JSONL / Parquet outputs
C. Runtime Layer

Docker-based runner pool
One isolated environment per run
Versioned images for framework and dependency control
D. Observability and Storage

Phoenix as tracing and evaluation base
OpenTelemetry + OpenInference for trace semantics
Postgres for run metadata, datasets, configs, and eval jobs
Optional object storage for snapshots and large artifacts
E. Agent / Tool Layer

OpenAI Agents SDK runtime
LangChain runtime
MCP servers and tool adapters
Module Responsibilities
Frontend:
Run Dashboard: filter, search, compare, launch runs and evals
Trajectory Viewer: inspect execution graph and node relationships
Eval UI: compare results and drill into failures
Backend:

Run Orchestrator: create runs, choose adapters, schedule runners, update states
Adapter Manager: normalize runtime events into a unified internal schema
Trace Gateway: ingest OTLP spans and enrich them with run metadata
Replay Service: rerun a single step with prompt/model/tool changes
Eval Service: score batches with rule-based, LLM-judge, and tool-correctness evaluators
Artifact Exporter: generate RL-ready trajectory outputs
Infrastructure:

Runner Pool: isolated execution with reproducible dependencies
Phoenix: trace storage, replay base, evaluation support
Postgres: control-plane metadata
Object Storage: exported datasets and snapshots

Recommended Open-Source Stack
Use instead of building from scratch:
Phoenix for tracing, replay, and evaluation foundation
OpenTelemetry for vendor-neutral telemetry
OpenInference for AI-semantic spans
OpenAI Agents SDK for built-in tracing-friendly runtime integration
LangChain for a second mainstream scaffold adapter
MCP ecosystem for tool interoperability
React Flow for trajectory graph UI
Monaco Editor for diff and prompt editing UI
Evaluation Methods in v1
Keep evaluation intentionally simple:
Rule-based matching
LLM-as-judge scoring
Tool correctness / execution success
This is enough to demonstrate product value without turning v1 into a research platform.

Data Model Sketch
Core entities:
run
span_index
dataset
eval_job
replay_job
artifact_export
Important normalized fields:

run_id
span_id
parent_span_id
step_type
input
output
tool_name
latency_ms
token_usage
image_digest
prompt_version
reward_stub
MVP Definition
The product is considered real once this loop works end-to-end:
User creates a run from the UI
Backend schedules a Docker runner
Agent emits traces automatically
Trace Gateway indexes the run
Phoenix receives and displays the trace
Frontend renders the trajectory
User replays a step and sees a diff
User can export the result as a training artifact
Success Metrics
Time to debug a failed run
Time to compare two runs
Time to integrate a new agent scaffold
Percentage of runs exportable as training data
Evaluation throughput per dataset batch
Product Positioning
Agent Flight Recorder is not a chatbot product. It is an engineering workbench for inspecting, replaying, evaluating, and exporting agent behavior.
The simplest positioning line is:
A self-hosted Agent Infra Workbench that connects external scaffolds to containerized execution, trajectory replay, evaluation, and RL-ready data export.
