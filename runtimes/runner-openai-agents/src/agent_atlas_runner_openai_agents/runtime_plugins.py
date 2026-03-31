from __future__ import annotations

from agent_atlas_runner_openai_agents.runtime import OpenAIAgentsSdkAdapter


def build_runtime_adapter_plugin() -> dict[str, object]:
    return {
        "adapter_kind": "openai-agents-sdk",
        "live_adapter": OpenAIAgentsSdkAdapter(),
    }


__all__ = ["build_runtime_adapter_plugin"]
