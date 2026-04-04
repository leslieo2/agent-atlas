from __future__ import annotations

from typing import Protocol

from app.modules.agents.application.ports import PublishedAgentRepositoryPort
from app.modules.agents.domain.models import (
    AgentModuleSource,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


class AgentSourceCatalog(Protocol):
    def list_sources(self) -> list[AgentModuleSource]: ...


class AgentContractValidator(Protocol):
    def discover(self, source: AgentModuleSource) -> DiscoveredAgent: ...


class StaticAgentDiscovery:
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
                        message=f"agent_id '{agent_id}' is declared by multiple sources",
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
        for persisted_agent in self.published_agents.list_agents():
            try:
                persisted_agent.source_fingerprint_or_raise()
                persisted_agent.execution_reference_or_raise()
            except ValueError:
                continue
            eligible[persisted_agent.agent_id] = persisted_agent
        return eligible
