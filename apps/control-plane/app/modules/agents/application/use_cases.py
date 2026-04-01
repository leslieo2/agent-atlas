from __future__ import annotations

from app.core.errors import (
    AgentValidationFailedError,
    PublishedAgentNotFoundError,
    UnsupportedOperationError,
)
from app.modules.agents.application.ports import (
    AgentSourceDiscoveryPort,
    PublishedAgentCatalogPort,
    PublishedAgentRepositoryPort,
)
from app.modules.agents.domain.models import (
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


class AgentDiscoveryQueries:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort | None,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def list_agents(self) -> list[DiscoveredAgent]:
        if self.discovery is None:
            return []
        published_by_id = {agent.agent_id: agent for agent in self.published_agents.list_agents()}
        discovered_agents = self.discovery.list_agents()
        enriched_agents: list[DiscoveredAgent] = []
        for agent in discovered_agents:
            published_agent = published_by_id.get(agent.agent_id)
            if published_agent is None or not _is_valid_published_agent(published_agent):
                enriched_agents.append(agent.with_publication(None))
                continue
            enriched_agents.append(agent.with_publication(published_agent))
        return enriched_agents


class PublishedAgentCatalogQueries:
    def __init__(self, published_agents: PublishedAgentCatalogPort) -> None:
        self.published_agents = published_agents

    def list_agents(self) -> list[PublishedAgent]:
        valid_agents = [
            agent
            for agent in self.published_agents.list_agents()
            if _is_valid_published_agent(agent)
        ]
        return sorted(valid_agents, key=lambda agent: agent.agent_id)


def _is_valid_published_agent(agent: PublishedAgent) -> bool:
    try:
        agent.source_fingerprint_or_raise()
        agent.execution_reference_or_raise()
    except ValueError:
        return False
    return True


class AgentPublicationCommands:
    def __init__(
        self,
        discovery: AgentSourceDiscoveryPort | None,
        published_agents: PublishedAgentRepositoryPort,
    ) -> None:
        self.discovery = discovery
        self.published_agents = published_agents

    def publish(self, agent_id: str) -> PublishedAgent:
        if self.discovery is None:
            raise UnsupportedOperationError(
                "repo-local agent discovery is not available in live mode",
                agent_id=agent_id,
            )
        discovered = self._get_discovered_agent(agent_id)
        if discovered.validation_status != AgentValidationStatus.VALID:
            issue_summary = "; ".join(issue.message for issue in discovered.validation_issues) or (
                "agent contract validation failed"
            )
            raise AgentValidationFailedError(agent_id=agent_id, message=issue_summary)

        existing = self.published_agents.get_agent(agent_id)
        published = discovered.to_published(existing=existing)
        self.published_agents.save_agent(published)
        return published

    def unpublish(self, agent_id: str) -> bool:
        deleted = self.published_agents.delete_agent(agent_id)
        if not deleted:
            raise PublishedAgentNotFoundError(agent_id)
        return True

    def _get_discovered_agent(self, agent_id: str) -> DiscoveredAgent:
        if self.discovery is None:
            raise UnsupportedOperationError(
                "repo-local agent discovery is not available in live mode",
                agent_id=agent_id,
            )
        for agent in self.discovery.list_agents():
            if agent.agent_id == agent_id:
                return agent
        raise AgentValidationFailedError(
            agent_id=agent_id,
            message=(
                f"agent '{agent_id}' is not available in the current repository-local "
                "discovery catalog"
            ),
        )
