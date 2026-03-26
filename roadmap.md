# Roadmap

## Current Product Direction

The near-term roadmap follows the registered-agent v1 product shape:

- Registered OpenAI Agents SDK agents as the primary runtime object
- Python registry-based agent catalog
- Playground flow driven by `agent_id`
- Local and Docker execution for registered agents
- Run dashboard and trajectory inspection for real executions
- JSONL export for successful runs

## Current Priorities

### 1. Registered Agent Catalog

Priority: High

Goal:
- Make repository-local OpenAI Agents SDK agents discoverable and selectable from the UI.

What this includes:
- A Python registry as the source of truth for registered agents
- `GET /api/v1/agents`
- Agent metadata visible in Playground and Run Dashboard
- Validation for missing or invalid entrypoints

Why this matters:
- This is the entry point into the product.
- Without a real catalog, the workbench cannot serve existing user-authored agents.

### 2. Registered-Agent Run Path

Priority: High

Goal:
- Execute a real registered agent from `agent_id` rather than from a platform-built mini runtime.

What this includes:
- `POST /api/v1/runs` driven by `agent_id`
- Runtime loading of repository-local Python entrypoints
- Local and Docker execution support
- Structured runtime error handling

Why this matters:
- This is the core product promise.
- It determines whether the workbench is truly an agent infrastructure tool or only a prompt playground.

### 3. Playground and Run Workspace

Priority: High

Goal:
- Make the main user workflow clear and reliable.

What this includes:
- Registered agent selector
- Prompt input
- Optional dataset selector
- Run creation from Playground
- Run workspace inspection of output, latency, token usage, and trajectory

Why this matters:
- This is the primary day-one workflow for users.
- It is the most visible expression of the new product shape.

### 4. JSONL Export

Priority: Medium

Goal:
- Turn successful runs into reusable engineering artifacts.

What this includes:
- Export selected runs as JSONL
- Include run metadata, agent metadata, and recorded execution steps
- Keep export semantics stable for downstream workflows

Why this matters:
- Export is the bridge from interactive debugging to downstream analysis and data pipelines.

## Post-v1 Backlog

### Registered-Agent Replay

Priority: Medium

Why this exists:
- Replay remains valuable for debugging and experimentation.
- It is intentionally out of the first registered-agent v1 scope.

What is missing:
- A replay contract for registered agents
- Stable replay semantics for agent-owned tools and state
- Clear UI behavior for replaying registered-agent runs

Implementation direction:
- Reintroduce replay only after the registered-agent run path is stable
- Base replay on `agent_id` and recorded execution metadata
- Avoid prompt-only replay semantics for agent-owned tool behavior

### Registered-Agent Eval

Priority: Medium

Why this exists:
- Dataset-based evaluation is important, but it should be built on top of a stable registered-agent execution path.

What is missing:
- Eval contracts centered on `agent_id`
- Batch execution over dataset samples
- Real scoring semantics rather than placeholder evaluation

Implementation direction:
- Add batch execution for registered agents
- Support rule-based and model-based evaluation only after run and export flows are stable

### Deterministic Tool Replay

Priority: Low

Why this exists:
- Deterministic replay of tool steps becomes important once registered-agent replay is a supported workflow.

What is missing:
- A dedicated tool replay backend
- Stable capture of tool input, tool output, and execution context
- A strategy for external state such as network responses and versioned dependencies

Implementation direction:
- Treat this as a follow-on to registered-agent replay
- Do not implement it as an isolated replay track ahead of the core registered-agent product path

### Additional Framework Support

Priority: Low

Why this exists:
- LangChain and MCP may become important once the registered OpenAI Agents SDK path is stable.

What is missing:
- A registry and runtime contract for non-OpenAI frameworks
- Clear compatibility rules for tool and trace semantics across frameworks

Implementation direction:
- Add LangChain first
- Consider MCP only after the product has a clearer multi-framework runtime story
