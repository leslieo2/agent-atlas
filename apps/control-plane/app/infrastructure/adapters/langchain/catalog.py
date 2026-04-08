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
from app.modules.shared.domain.enums import AdapterKind, AgentFamily


class LangChainAgentContractValidator(BaseAgentContractValidator):
    def __init__(self) -> None:
        super().__init__(module_loader=lambda module_name: import_module(module_name))

    def _manifest_issues(self, manifest: AgentManifest) -> list[AgentValidationIssue]:
        if manifest.framework != AdapterKind.LANGCHAIN.value:
            return [
                AgentValidationIssue(
                    code="framework_invalid",
                    message="langchain validator requires manifest framework to be 'langchain'",
                )
            ]
        return []

    def _validate_build_agent(
        self,
        *,
        build_agent: Any,
        entrypoint: str,
        agent_id: str,
    ) -> list[AgentValidationIssue]:
        del agent_id
        try:
            candidate = build_agent(validation_context())
        except Exception as exc:
            return [
                AgentValidationIssue(
                    code="build_agent_failed",
                    message=f"entrypoint '{entrypoint}' failed during validation: {exc}",
                )
            ]

        if not self._is_supported_runtime(candidate):
            return [
                AgentValidationIssue(
                    code="build_agent_invalid_return",
                    message=(
                        f"entrypoint '{entrypoint}' did not return a LangGraph/LangChain runnable"
                    ),
                )
            ]
        return []

    @staticmethod
    def _is_supported_runtime(candidate: Any) -> bool:
        invoke = getattr(candidate, "invoke", None)
        return callable(invoke) or callable(candidate)

    def _invalid_manifest(self, module_name: str) -> AgentManifest:
        module_leaf = module_name.rsplit(".", 1)[-1]
        return AgentManifest(
            agent_id=module_leaf,
            name=module_leaf.replace("_", " ").title(),
            description="Invalid agent manifest",
            agent_family=AgentFamily.LANGCHAIN.value,
            framework=AdapterKind.LANGCHAIN.value,
            default_model="",
            tags=[],
        )


class PublishedLangChainAgentLoader(BasePublishedAgentLoader[LangChainAgentContractValidator]):
    pass
