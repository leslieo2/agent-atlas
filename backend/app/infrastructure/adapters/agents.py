from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pkgutil import iter_modules
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.core.errors import AgentLoadFailedError
from app.modules.agents.application.ports import PublishedAgentRepositoryPort
from app.modules.agents.domain.models import (
    AgentBuildContext,
    AgentManifest,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


def _validation_context() -> AgentBuildContext:
    return AgentBuildContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        project="validation",
        dataset=None,
        prompt="validation",
        tags=[],
        project_metadata={},
    )


@dataclass(frozen=True)
class AgentModuleSource:
    module_name: str
    entrypoint: str


class FilesystemAgentSourceCatalog:
    package_name = "app.agent_plugins"

    def list_sources(self) -> list[AgentModuleSource]:
        package = import_module(self.package_name)
        package_paths = getattr(package, "__path__", None)
        if package_paths is None:
            return []

        sources: list[AgentModuleSource] = []
        for module_info in iter_modules(package_paths, f"{self.package_name}."):
            module_leaf = module_info.name.rsplit(".", 1)[-1]
            if module_leaf.startswith("_"):
                continue
            sources.append(
                AgentModuleSource(
                    module_name=module_info.name,
                    entrypoint=f"{module_info.name}:build_agent",
                )
            )
        return sorted(sources, key=lambda source: source.module_name)


class OpenAIAgentContractValidator:
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
        agent_id: str,
    ) -> list[AgentValidationIssue]:
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
            candidate = build_agent(_validation_context())
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
            default_model=str(fallback.get("default_model") or ""),
            tags=normalized_tags,
        )


class FilesystemAgentDiscovery:
    def __init__(
        self,
        source_catalog: FilesystemAgentSourceCatalog,
        validator: OpenAIAgentContractValidator,
    ) -> None:
        self.source_catalog = source_catalog
        self.validator = validator

    def list_agents(self) -> list[DiscoveredAgent]:
        discovered = [
            self.validator.discover(source) for source in self.source_catalog.list_sources()
        ]
        duplicates: dict[str, list[int]] = {}
        for index, agent in enumerate(discovered):
            duplicates.setdefault(agent.agent_id, []).append(index)

        for agent_id, indexes in duplicates.items():
            if len(indexes) < 2:
                continue
            for index in indexes:
                current = discovered[index]
                issues = list(current.validation_issues)
                issues.append(
                    AgentValidationIssue(
                        code="duplicate_agent_id",
                        message=f"agent_id '{agent_id}' is declared by multiple plugin modules",
                    )
                )
                discovered[index] = current.model_copy(
                    update={
                        "validation_status": AgentValidationStatus.INVALID,
                        "validation_issues": issues,
                    }
                )

        return sorted(discovered, key=lambda agent: agent.agent_id)


class StateRunnableAgentCatalog:
    def __init__(
        self,
        discovery: FilesystemAgentDiscovery,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def list_agents(self) -> list[PublishedAgent]:
        published_by_id = {agent.agent_id: agent for agent in self.published_agents.list_agents()}
        runnable_ids = {
            agent.agent_id
            for agent in self.discovery.list_agents()
            if agent.validation_status == AgentValidationStatus.VALID
        }
        return [
            published_by_id[agent_id]
            for agent_id in sorted(runnable_ids)
            if agent_id in published_by_id
        ]

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        published = self.published_agents.get_agent(agent_id)
        if published is None:
            return None

        for discovered in self.discovery.list_agents():
            if (
                discovered.agent_id == agent_id
                and discovered.validation_status == AgentValidationStatus.VALID
            ):
                return published
        return None


class PublishedOpenAIAgentLoader:
    def __init__(self, validator: OpenAIAgentContractValidator) -> None:
        self.validator = validator

    def build_agent(self, *, published_agent: PublishedAgent, context: AgentBuildContext) -> Any:
        return self.validator.build_agent(
            entrypoint=published_agent.entrypoint,
            context=context,
            agent_id=published_agent.agent_id,
        )
