from __future__ import annotations

from typing import Any, cast

from agent_atlas_runner_openai_agents.runtime import PublishedOpenAIAgentAdapter

from app.modules.agents.domain.constants import CLAUDE_CODE_CLI_FRAMEWORK

from ..framework_registry import FrameworkPlugin
from ..openai_agents.catalog import OpenAIAgentContractValidator, PublishedOpenAIAgentLoader


def build_framework_plugin() -> FrameworkPlugin:
    validator = OpenAIAgentContractValidator()
    loader = PublishedOpenAIAgentLoader(validator=validator)
    return FrameworkPlugin(
        framework=CLAUDE_CODE_CLI_FRAMEWORK,
        validator=validator,
        loader=loader,
        runtime=cast(
            Any,
            PublishedOpenAIAgentAdapter(agent_loader=cast(Any, loader)),
        ),
    )


__all__ = [
    "OpenAIAgentContractValidator",
    "PublishedOpenAIAgentAdapter",
    "PublishedOpenAIAgentLoader",
    "build_framework_plugin",
]
