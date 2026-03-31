from __future__ import annotations

from agent_atlas_runner_langgraph.runtime import LangChainRuntimeAdapter


def build_runtime_adapter_plugin() -> dict[str, object]:
    return {
        "adapter_kind": "langchain",
        "live_adapter": LangChainRuntimeAdapter(),
    }


__all__ = ["build_runtime_adapter_plugin"]
