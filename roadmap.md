# Roadmap

## Current Product Direction

The near-term roadmap follows the scanned-and-published agent v1 product shape:

- Repository-local OpenAI Agents SDK agent plugins as the primary runtime object
- Automatic discovery plus explicit publish / unpublish workflow
- Published runnable agent catalog
- Playground flow driven by `agent_id`
- Local and Docker execution for published agents
- Agent Management workspace for discovery and publication
- Run dashboard and trajectory inspection for real executions
- JSONL export for successful runs

## Current Priorities

### 1. Agent Discovery and Publication

Priority: High

Goal:
- Make repository-local OpenAI Agents SDK agent plugins discoverable, validatable, and publishable from the UI.

What this includes:
- Filesystem scanning of `backend/app/agent_plugins/`
- A fixed plugin contract: `AGENT_MANIFEST` plus `build_agent(context) -> Agent`
- `GET /api/v1/agents/discovered`
- `GET /api/v1/agents`
- `POST /api/v1/agents/{agent_id}/publish`
- `POST /api/v1/agents/{agent_id}/unpublish`
- Validation for missing or invalid manifests and entrypoints

Why this matters:
- This is the entry point into the product.
- Without a real discovery and publication workflow, the workbench cannot safely serve existing user-authored agents.

### 2. Published-Agent Run Path

Priority: High

Goal:
- Execute a real published agent from `agent_id` rather than from a platform-built mini runtime.

What this includes:
- `POST /api/v1/runs` driven by `agent_id`
- Runtime loading driven by the published catalog
- Local and Docker execution support
- Structured runtime error handling

Why this matters:
- This is the core product promise.
- It determines whether the workbench is truly an agent infrastructure tool or only a prompt playground.

### 3. Agent Management, Playground, and Run Workspace

Priority: High

Goal:
- Make the main user workflow clear and reliable.

What this includes:
- Agent Management workspace with Draft, Published, and Invalid states
- Publish / Unpublish actions
- Published agent selector
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
- Include run metadata, published-agent metadata, and recorded execution steps
- Keep export semantics stable for downstream workflows

Why this matters:
- Export is the bridge from interactive debugging to downstream analysis and data pipelines.

## Post-v1 Backlog

### Published-Agent Replay

Priority: Medium

Why this exists:
- Replay remains valuable for debugging and experimentation.
- It is intentionally out of the first scanned-and-published v1 scope.

What is missing:
- A replay contract for published agents
- Stable replay semantics for agent-owned tools and state
- Clear UI behavior for replaying published-agent runs

Implementation direction:
- Reintroduce replay only after the published-agent run path is stable
- Base replay on `agent_id` and recorded execution metadata
- Avoid prompt-only replay semantics for agent-owned tool behavior

### Published-Agent Eval

Priority: Medium

Why this exists:
- Dataset-based evaluation is important, but it should be built on top of a stable published-agent execution path.

What is missing:
- Eval contracts centered on `agent_id`
- Batch execution over dataset samples
- Real scoring semantics rather than placeholder evaluation

Implementation direction:
- Add batch execution for published agents
- Support rule-based and model-based evaluation only after run and export flows are stable

### Deterministic Tool Replay

Priority: Low

Why this exists:
- Deterministic replay of tool steps becomes important once published-agent replay is a supported workflow.

What is missing:
- A dedicated tool replay backend
- Stable capture of tool input, tool output, and execution context
- A strategy for external state such as network responses and versioned dependencies

Implementation direction:
- Treat this as a follow-on to published-agent replay
- Do not implement it as an isolated replay track ahead of the core scanned-and-published product path

### Versioned Agent Publication

Priority: Low

Why this exists:
- Publication currently controls platform exposure, not code freezing.
- Teams may later need auditable, reproducible publish artifacts.

What is missing:
- Manifest version history
- Source snapshots or content hashing
- Clear rollback semantics for a previously published agent revision

Implementation direction:
- Add after discovery, publication, and run flows are stable
- Keep v1 publish lightweight and runtime-oriented first

### Additional Agent Sources

Priority: Low

Why this exists:
- Some teams will eventually want to source agents from installed packages or remote repositories.

What is missing:
- A safe source abstraction beyond repository-local Python modules
- Trust, isolation, and compatibility rules for external sources

Implementation direction:
- Keep v1 constrained to `backend/app/agent_plugins/`
- Add new sources only after the repository-local plugin path is stable

### Additional Framework Support

Priority: Low

Why this exists:
- LangChain and MCP may become important once the repository-local OpenAI Agents SDK plugin path is stable.

What is missing:
- A plugin contract and runtime contract for non-OpenAI frameworks
- Clear compatibility rules for tool and trace semantics across frameworks

Implementation direction:
- Add LangChain first
- Consider MCP only after the product has a clearer multi-framework runtime story
