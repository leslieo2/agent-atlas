from __future__ import annotations

from typing import Any, cast

from ..framework_registry import FrameworkPlugin
from .catalog import LangChainAgentContractValidator, PublishedLangChainAgentLoader
from .runtime import LangChainRuntimeAdapter, PublishedLangChainAgentAdapter
from .trace_mapper import build_trace_events_from_langgraph_run


def build_framework_plugin() -> FrameworkPlugin:
    validator = LangChainAgentContractValidator()
    loader = PublishedLangChainAgentLoader(validator=validator)
    return FrameworkPlugin(
        framework="langchain",
        validator=validator,
        loader=loader,
        runtime=cast(
            Any,
            PublishedLangChainAgentAdapter(agent_loader=cast(Any, loader)),
        ),
    )


__all__ = [
    "LangChainAgentContractValidator",
    "LangChainRuntimeAdapter",
    "PublishedLangChainAgentAdapter",
    "PublishedLangChainAgentLoader",
    "build_framework_plugin",
    "build_trace_events_from_langgraph_run",
]
