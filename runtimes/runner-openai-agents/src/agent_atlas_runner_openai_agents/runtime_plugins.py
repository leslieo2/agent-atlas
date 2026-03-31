from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_runner_openai_agents.runtime import OpenAIAgentsSdkAdapter


@dataclass(frozen=True)
class RuntimeAdapterPluginSpec:
    adapter_kind: str
    live_adapter: OpenAIAgentsSdkAdapter


def build_runtime_adapter_plugin() -> RuntimeAdapterPluginSpec:
    return RuntimeAdapterPluginSpec(
        adapter_kind="openai-agents-sdk",
        live_adapter=OpenAIAgentsSdkAdapter(),
    )


__all__ = ["build_runtime_adapter_plugin"]
