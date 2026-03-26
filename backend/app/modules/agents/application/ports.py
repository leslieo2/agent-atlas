from __future__ import annotations

from typing import Protocol

from app.modules.agents.domain.models import DiscoveredAgent, PublishedAgent


class AgentSourceDiscoveryPort(Protocol):
    def list_agents(self) -> list[DiscoveredAgent]: ...


class PublishedAgentRepositoryPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...

    def save_agent(self, agent: PublishedAgent) -> None: ...

    def delete_agent(self, agent_id: str) -> bool: ...


class RunnableAgentCatalogPort(Protocol):
    def list_agents(self) -> list[PublishedAgent]: ...

    def get_agent(self, agent_id: str) -> PublishedAgent | None: ...
