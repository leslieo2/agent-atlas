from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from typing import Protocol

from app.modules.agents.application.ports import (
    AgentSourceDiscoveryPort,
    LiveAgentMarkerRepositoryPort,
    PublishedAgentRepositoryPort,
)
from app.modules.agents.domain.models import (
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_manifest,
    claude_code_starter_runtime_profile,
)


class AgentSourceCatalog(Protocol):
    def list_sources(self) -> list[AgentModuleSource]: ...


class AgentContractValidator(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...


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


class FilesystemAgentDiscovery:
    def __init__(
        self,
        source_catalog: AgentSourceCatalog,
        validator: AgentContractValidator,
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


class StatePublishedAgentCatalog:
    def __init__(
        self,
        published_agents: PublishedAgentRepositoryPort,
        discovery: AgentSourceDiscoveryPort | None = None,
    ) -> None:
        self.published_agents = published_agents
        self.discovery = discovery

    def list_agents(self) -> list[PublishedAgent]:
        eligible_by_id = self._eligible_published_by_id()
        return sorted(
            [
                agent
                for agent in self.published_agents.list_agents()
                if agent.agent_id in eligible_by_id
            ],
            key=lambda agent: agent.agent_id,
        )

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return self._eligible_published_by_id().get(agent_id)

    def _eligible_published_by_id(self) -> dict[str, PublishedAgent]:
        eligible: dict[str, PublishedAgent] = {}
        published_by_id = {agent.agent_id: agent for agent in self.published_agents.list_agents()}
        if self.discovery is None:
            for persisted_agent in published_by_id.values():
                try:
                    persisted_agent.source_fingerprint_or_raise()
                    persisted_agent.execution_reference_or_raise()
                except ValueError:
                    continue
                eligible[persisted_agent.agent_id] = persisted_agent
            return eligible

        for discovered_agent in self.discovery.list_agents():
            if discovered_agent.validation_status != AgentValidationStatus.VALID:
                continue
            matched_published_agent = published_by_id.get(discovered_agent.agent_id)
            if matched_published_agent is None:
                continue
            try:
                source_fingerprint = matched_published_agent.source_fingerprint_or_raise()
                matched_published_agent.execution_reference_or_raise()
            except ValueError:
                continue
            if discovered_agent.source_fingerprint() != source_fingerprint:
                continue
            eligible[matched_published_agent.agent_id] = matched_published_agent
        return eligible


class StateLiveAgentDiscovery:
    def __init__(self, markers: LiveAgentMarkerRepositoryPort) -> None:
        self.markers = markers

    def list_agents(self) -> list[DiscoveredAgent]:
        discovered: list[DiscoveredAgent] = []
        for agent_id in self.markers.list_agent_ids():
            if agent_id != CLAUDE_CODE_STARTER_AGENT_ID:
                continue
            discovered.append(
                DiscoveredAgent(
                    manifest=claude_code_starter_manifest(),
                    entrypoint=CLAUDE_CODE_STARTER_ENTRYPOINT,
                    validation_status=AgentValidationStatus.VALID,
                    validation_issues=[],
                    default_runtime_profile=claude_code_starter_runtime_profile(),
                )
            )
        return sorted(discovered, key=lambda agent: agent.agent_id)


class StateLivePublishedAgentCatalog:
    def __init__(
        self,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.published_agents = published_agents

    def list_agents(self) -> list[PublishedAgent]:
        eligible_by_id = self._eligible_published_by_id()
        return sorted(
            [
                agent
                for agent in self.published_agents.list_agents()
                if agent.agent_id in eligible_by_id
            ],
            key=lambda agent: agent.agent_id,
        )

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return self._eligible_published_by_id().get(agent_id)

    def _eligible_published_by_id(self) -> dict[str, PublishedAgent]:
        eligible: dict[str, PublishedAgent] = {}
        for published_agent in self.published_agents.list_agents():
            try:
                published_agent.source_fingerprint_or_raise()
                published_agent.execution_reference_or_raise()
            except ValueError:
                continue
            eligible[published_agent.agent_id] = published_agent
        return eligible
