from __future__ import annotations

from importlib import import_module
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.core.errors import AgentLoadFailedError
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.shared.domain.enums import AdapterKind


def _validation_context() -> AgentBuildContext:
    return AgentBuildContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        project="validation",
        dataset=None,
        prompt="validation",
        tags=[],
        project_metadata={},
    )


class LangChainAgentContractValidator:
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
        issues: list[AgentValidationIssue] = []

        try:
            module = import_module(source.module_name)
        except Exception as exc:
            return DiscoveredAgent(
                manifest=self._fallback_manifest(source.module_name),
                entrypoint=source.entrypoint,
                validation_status=AgentValidationStatus.INVALID,
                validation_issues=[
                    AgentValidationIssue(
                        code="module_import_failed",
                        message=f"failed to import module '{source.module_name}': {exc}",
                    )
                ],
            )

        manifest, manifest_issues = self._read_manifest(
            module=module,
            module_name=source.module_name,
        )
        issues.extend(manifest_issues)

        build_agent = getattr(module, "build_agent", None)
        if build_agent is None:
            issues.append(
                AgentValidationIssue(
                    code="build_agent_missing",
                    message=f"module '{source.module_name}' does not export build_agent(context)",
                )
            )
        elif not callable(build_agent):
            issues.append(
                AgentValidationIssue(
                    code="build_agent_not_callable",
                    message=f"symbol 'build_agent' in '{source.module_name}' is not callable",
                )
            )
        else:
            issues.extend(
                self._validate_build_agent(
                    build_agent=build_agent,
                    entrypoint=source.entrypoint,
                )
            )

        return DiscoveredAgent(
            manifest=manifest,
            entrypoint=source.entrypoint,
            validation_status=(
                AgentValidationStatus.VALID if not issues else AgentValidationStatus.INVALID
            ),
            validation_issues=issues,
        )

    def build_agent(
        self,
        *,
        entrypoint: str,
        context: AgentBuildContext,
        agent_id: str,
    ) -> Any:
        build_agent = self._load_build_agent(entrypoint=entrypoint, agent_id=agent_id)
        try:
            return build_agent(context)
        except Exception as exc:
            raise AgentLoadFailedError(
                f"failed to build published agent '{agent_id}'",
                agent_id=agent_id,
                entrypoint=entrypoint,
            ) from exc

    def _load_build_agent(self, *, entrypoint: str, agent_id: str) -> Any:
        module_name, _, symbol_name = entrypoint.partition(":")
        if not module_name or not symbol_name:
            raise AgentLoadFailedError(
                f"invalid entrypoint '{entrypoint}'",
                agent_id=agent_id,
                entrypoint=entrypoint,
            )

        try:
            module = import_module(module_name)
        except Exception as exc:
            raise AgentLoadFailedError(
                f"failed to import module '{module_name}'",
                agent_id=agent_id,
                entrypoint=entrypoint,
            ) from exc

        symbol = getattr(module, symbol_name, None)
        if symbol is None:
            raise AgentLoadFailedError(
                f"symbol '{symbol_name}' not found in module '{module_name}'",
                agent_id=agent_id,
                entrypoint=entrypoint,
            )
        if not callable(symbol):
            raise AgentLoadFailedError(
                f"symbol '{symbol_name}' is not callable",
                agent_id=agent_id,
                entrypoint=entrypoint,
            )
        return symbol

    def _read_manifest(
        self,
        *,
        module: Any,
        module_name: str,
    ) -> tuple[AgentManifest, list[AgentValidationIssue]]:
        raw_manifest = getattr(module, "AGENT_MANIFEST", None)
        if raw_manifest is None:
            return (
                self._fallback_manifest(module_name),
                [
                    AgentValidationIssue(
                        code="manifest_missing",
                        message=f"module '{module_name}' does not define AGENT_MANIFEST",
                    )
                ],
            )

        try:
            manifest = AgentManifest.model_validate(raw_manifest)
        except ValidationError as exc:
            return (
                self._fallback_manifest(module_name, raw_manifest=raw_manifest),
                [
                    AgentValidationIssue(
                        code="manifest_invalid",
                        message=f"AGENT_MANIFEST in '{module_name}' is invalid: {exc.errors()}",
                    )
                ],
            )

        issues: list[AgentValidationIssue] = []
        if manifest.framework != AdapterKind.LANGCHAIN.value:
            issues.append(
                AgentValidationIssue(
                    code="framework_invalid",
                    message="langchain validator requires manifest framework to be 'langchain'",
                )
            )
        if not manifest.agent_id.strip():
            issues.append(
                AgentValidationIssue(
                    code="manifest_invalid",
                    message="manifest agent_id must be set",
                )
            )
        if not manifest.name.strip():
            issues.append(
                AgentValidationIssue(code="manifest_invalid", message="manifest name must be set")
            )
        if not manifest.description.strip():
            issues.append(
                AgentValidationIssue(
                    code="manifest_invalid",
                    message="manifest description must be set",
                )
            )
        if not manifest.default_model.strip():
            issues.append(
                AgentValidationIssue(
                    code="manifest_invalid",
                    message="manifest default_model must be set",
                )
            )
        return manifest, issues

    def _validate_build_agent(
        self,
        *,
        build_agent: Any,
        entrypoint: str,
    ) -> list[AgentValidationIssue]:
        try:
            candidate = build_agent(_validation_context())
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

    def _fallback_manifest(
        self,
        module_name: str,
        raw_manifest: object | None = None,
    ) -> AgentManifest:
        fallback = raw_manifest if isinstance(raw_manifest, dict) else {}
        module_leaf = module_name.rsplit(".", 1)[-1]
        default_name = module_leaf.replace("_", " ").title()
        tags = fallback.get("tags", [])
        normalized_tags = [str(tag) for tag in tags] if isinstance(tags, list) else []
        return AgentManifest(
            agent_id=str(fallback.get("agent_id") or module_leaf),
            name=str(fallback.get("name") or default_name),
            description=str(fallback.get("description") or "Invalid agent manifest"),
            framework=str(fallback.get("framework") or AdapterKind.LANGCHAIN.value),
            default_model=str(fallback.get("default_model") or ""),
            tags=normalized_tags,
        )


class PublishedLangChainAgentLoader:
    def __init__(self, validator: LangChainAgentContractValidator) -> None:
        self.validator = validator

    def build_agent(self, *, published_agent: PublishedAgent, context: AgentBuildContext) -> Any:
        return self.validator.build_agent(
            entrypoint=published_agent.entrypoint,
            context=context,
            agent_id=published_agent.agent_id,
        )
