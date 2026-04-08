from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar
from uuid import UUID

from agent_atlas_contracts.runtime import (
    AgentBuildContext,
    AgentLoadFailedError,
    AgentManifest,
)
from agent_atlas_contracts.runtime import PublishedAgent as ContractPublishedAgentSnapshot
from pydantic import ValidationError

from app.modules.agents.domain.models import (
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
)

ValidatorT = TypeVar("ValidatorT", bound="BaseAgentContractValidator")


def validation_context() -> AgentBuildContext:
    return AgentBuildContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        project="validation",
        dataset=None,
        prompt="validation",
        tags=[],
        project_metadata={},
    )


class BaseAgentContractValidator:
    def __init__(self, module_loader: Callable[[str], Any]) -> None:
        self._module_loader = module_loader

    def discover(self, source: AgentModuleSource) -> DiscoveredAgent:
        issues: list[AgentValidationIssue] = []

        try:
            module = self._module_loader(source.module_name)
        except Exception as exc:
            return DiscoveredAgent(
                manifest=self._invalid_manifest(source.module_name),
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
                    agent_id=manifest.agent_id,
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
            module = self._module_loader(module_name)
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
                self._invalid_manifest(module_name),
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
                self._invalid_manifest(module_name),
                [
                    AgentValidationIssue(
                        code="manifest_invalid",
                        message=f"AGENT_MANIFEST in '{module_name}' is invalid: {exc.errors()}",
                    )
                ],
            )

        issues = self._manifest_issues(manifest)
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

    def _manifest_issues(self, manifest: AgentManifest) -> list[AgentValidationIssue]:
        del manifest
        return []

    def _validate_build_agent(
        self,
        *,
        build_agent: Any,
        entrypoint: str,
        agent_id: str,
    ) -> list[AgentValidationIssue]:
        raise NotImplementedError

    def _invalid_manifest(self, module_name: str) -> AgentManifest:
        raise NotImplementedError


class BasePublishedAgentLoader(Generic[ValidatorT]):
    def __init__(self, validator: ValidatorT) -> None:
        self.validator = validator

    def build_agent(
        self,
        *,
        published_agent: ContractPublishedAgentSnapshot,
        context: AgentBuildContext,
    ) -> Any:
        return self.validator.build_agent(
            entrypoint=published_agent.entrypoint,
            context=context,
            agent_id=published_agent.agent_id,
        )
