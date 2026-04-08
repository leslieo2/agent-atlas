from __future__ import annotations

from importlib import import_module
from typing import Any

from agent_atlas_contracts.runtime import AgentManifest

from app.infrastructure.adapters.framework_contracts import (
    BaseAgentContractValidator,
    BasePublishedAgentLoader,
    validation_context,
)
from app.modules.agents.domain.models import AgentValidationIssue
from app.modules.shared.domain.enums import AgentFamily


class OpenAIAgentContractValidator(BaseAgentContractValidator):
    def __init__(self) -> None:
        super().__init__(module_loader=lambda module_name: import_module(module_name))

    def _validate_build_agent(
        self,
        *,
        build_agent: Any,
        entrypoint: str,
        agent_id: str,
    ) -> list[AgentValidationIssue]:
        del agent_id
        try:
            from agents import Agent
        except ImportError:
            return [
                AgentValidationIssue(
                    code="sdk_missing",
                    message="OpenAI Agents SDK package 'agents' is not installed",
                )
            ]

        try:
            candidate = build_agent(validation_context())
        except Exception as exc:
            return [
                AgentValidationIssue(
                    code="build_agent_failed",
                    message=f"entrypoint '{entrypoint}' failed during validation: {exc}",
                )
            ]

        if not isinstance(candidate, Agent):
            return [
                AgentValidationIssue(
                    code="build_agent_invalid_return",
                    message=(
                        f"entrypoint '{entrypoint}' did not return an OpenAI Agents SDK Agent"
                    ),
                )
            ]
        return []

    def _invalid_manifest(self, module_name: str) -> AgentManifest:
        module_leaf = module_name.rsplit(".", 1)[-1]
        return AgentManifest(
            agent_id=module_leaf,
            name=module_leaf.replace("_", " ").title(),
            description="Invalid agent manifest",
            agent_family=AgentFamily.OPENAI_AGENTS.value,
            framework="openai-agents-sdk",
            default_model="",
            tags=[],
        )


class PublishedOpenAIAgentLoader(BasePublishedAgentLoader[OpenAIAgentContractValidator]):
    pass
