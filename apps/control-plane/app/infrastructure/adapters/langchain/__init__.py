from __future__ import annotations

from typing import Any, cast

from agent_atlas_runner_langgraph.runtime import (
    LangChainRuntimeAdapter,
    PublishedLangChainAgentAdapter,
)
from agent_atlas_runner_langgraph.trace_mapper import build_trace_events_from_langgraph_run

from ..framework_registry import FrameworkPlugin
from .catalog import LangChainAgentContractValidator, PublishedLangChainAgentLoader


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
