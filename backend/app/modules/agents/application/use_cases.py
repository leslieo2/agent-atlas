from __future__ import annotations

from app.core.errors import AgentValidationFailedError
from app.modules.agents.application.ports import (
    AgentSourceDiscoveryPort,
    PublishedAgentRepositoryPort,
    RunnableAgentCatalogPort,
)
from app.modules.agents.domain.models import (
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


class AgentDiscoveryQueries:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def list_agents(self) -> list[DiscoveredAgent]:
        published_by_id = {agent.agent_id: agent for agent in self.published_agents.list_agents()}
        discovered_agents = self.discovery.list_agents()
        return [
            agent.with_publication(published_by_id.get(agent.agent_id))
            for agent in discovered_agents
        ]


class AgentCatalogQueries:
    def __init__(self, runnable_catalog: RunnableAgentCatalogPort) -> None:
        self.runnable_catalog = runnable_catalog

    def list_agents(self) -> list[PublishedAgent]:
        return self.runnable_catalog.list_agents()


class AgentPublicationCommands:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def publish(self, agent_id: str) -> PublishedAgent:
        discovered = self._get_discovered_agent(agent_id)
        if discovered.validation_status != AgentValidationStatus.VALID:
            issue_summary = "; ".join(issue.message for issue in discovered.validation_issues) or (
                "agent contract validation failed"
            )
            raise AgentValidationFailedError(agent_id=agent_id, message=issue_summary)

        published = discovered.to_published()
        self.published_agents.save_agent(published)
        return published

    def unpublish(self, agent_id: str) -> bool:
        return self.published_agents.delete_agent(agent_id)

    def _get_discovered_agent(self, agent_id: str) -> DiscoveredAgent:
        for agent in self.discovery.list_agents():
            if agent.agent_id == agent_id:
                return agent
        raise AgentValidationFailedError(
            agent_id=agent_id,
            message=f"agent_id '{agent_id}' was not discovered under app.agent_plugins",
        )
