from __future__ import annotations

from app.infrastructure.repositories.common import persistence
from app.modules.agents.domain.models import PublishedAgent


class StatePublishedAgentRepository:
    def list_agents(self) -> list[PublishedAgent]:
        return persistence.list_published_agents()

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return persistence.get_published_agent(agent_id)

    def save_agent(self, agent: PublishedAgent) -> None:
        persistence.save_published_agent(agent)

    def delete_agent(self, agent_id: str) -> bool:
        return persistence.delete_published_agent(agent_id)
