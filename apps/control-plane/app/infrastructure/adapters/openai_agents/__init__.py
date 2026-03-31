from __future__ import annotations

from typing import Any, cast

from agent_atlas_runner_openai_agents.runtime import (
    OpenAIAgentsSdkAdapter,
    PublishedOpenAIAgentAdapter,
)
from agent_atlas_runner_openai_agents.trace_mapper import build_trace_events_from_agent_run

from ..framework_registry import FrameworkPlugin
from .catalog import OpenAIAgentContractValidator, PublishedOpenAIAgentLoader


def build_framework_plugin() -> FrameworkPlugin:
    validator = OpenAIAgentContractValidator()
    loader = PublishedOpenAIAgentLoader(validator=validator)
    return FrameworkPlugin(
        framework="openai-agents-sdk",
        validator=validator,
        loader=loader,
        runtime=cast(
            Any,
            PublishedOpenAIAgentAdapter(agent_loader=cast(Any, loader)),
        ),
    )


__all__ = [
    "OpenAIAgentContractValidator",
    "OpenAIAgentsSdkAdapter",
    "PublishedOpenAIAgentAdapter",
    "PublishedOpenAIAgentLoader",
    "build_framework_plugin",
    "build_trace_events_from_agent_run",
]
