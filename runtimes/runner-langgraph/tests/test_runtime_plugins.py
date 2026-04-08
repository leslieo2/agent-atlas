from __future__ import annotations

from agent_atlas_runner_langgraph.runtime import LangChainRuntimeAdapter
from agent_atlas_runner_langgraph.runtime_plugins import build_runtime_adapter_plugin


def test_build_runtime_adapter_plugin_returns_langchain_adapter() -> None:
    plugin = build_runtime_adapter_plugin()

    assert plugin.adapter_kind == "langchain"
    assert isinstance(plugin.live_adapter, LangChainRuntimeAdapter)

