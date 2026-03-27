from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pkgutil import iter_modules
from typing import Protocol

from app.modules.agents.application.ports import PublishedAgentRepositoryPort
from app.modules.agents.domain.models import (
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


@dataclass(frozen=True)
class AgentModuleSource:
    module_name: str
    entrypoint: str


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
