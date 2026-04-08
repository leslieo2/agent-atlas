from __future__ import annotations

from agent_atlas_runner_openai_agents.runtime import OpenAIAgentsSdkAdapter
from agent_atlas_runner_openai_agents.runtime_plugins import build_runtime_adapter_plugin


def test_build_runtime_adapter_plugin_returns_openai_adapter() -> None:
    plugin = build_runtime_adapter_plugin()

    assert plugin.adapter_kind == "openai-agents-sdk"
    assert isinstance(plugin.live_adapter, OpenAIAgentsSdkAdapter)

