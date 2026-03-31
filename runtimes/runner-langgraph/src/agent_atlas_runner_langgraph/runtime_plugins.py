from __future__ import annotations

from dataclasses import dataclass

from agent_atlas_runner_langgraph.runtime import LangChainRuntimeAdapter


@dataclass(frozen=True)
class RuntimeAdapterPluginSpec:
    adapter_kind: str
    live_adapter: LangChainRuntimeAdapter


def build_runtime_adapter_plugin() -> RuntimeAdapterPluginSpec:
    return RuntimeAdapterPluginSpec(
        adapter_kind="langchain",
        live_adapter=LangChainRuntimeAdapter(),
    )


__all__ = ["build_runtime_adapter_plugin"]
