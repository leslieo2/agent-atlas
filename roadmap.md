# Roadmap

## Future Work

### Deterministic Tool Step Replay

Priority: Medium

Why this exists:
- Current step replay is already a real runtime call, not a fake string response.
- But `TOOL` step replay still works by sending a replay prompt through the original adapter runner.
- That means it is useful for debugging, but it is not yet a strict, deterministic rerun of the original tool call.

What is missing:
- A dedicated tool execution backend for replaying `TOOL` steps directly.
- Native MCP/tool runtime support instead of replay-via-prompt.
- Reuse of original tool name, tool input, config, and execution context.
- Better control over external state such as network responses, timestamps, and tool server versions.

Why it is not the top priority right now:
- The current replay path already delivers core PRD value for debug-and-replay.
- Higher-priority work remains around end-to-end product completeness and reliability.
- This becomes high priority when tool failures or MCP reproducibility become a major debugging bottleneck.

Implementation direction:
- Add a replay-time tool runtime abstraction for `TOOL` steps.
- Route `LLM` and `TOOL` replay through different execution backends.
- Persist richer step baseline data needed for deterministic replay.
- Add tests that verify the same tool input can be replayed without going through prompt synthesis.
