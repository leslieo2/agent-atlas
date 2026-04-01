from __future__ import annotations

from typing import cast

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence
from app.modules.agents.domain.models import PublishedAgent

state_persistence = cast(StatePersistence, persistence)


class StatePublishedAgentRepository:
    def list_agents(self) -> list[PublishedAgent]:
        return state_persistence.list_published_agents()

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return state_persistence.get_published_agent(agent_id)

    def save_agent(self, agent: PublishedAgent) -> None:
        state_persistence.save_published_agent(agent)

    def delete_agent(self, agent_id: str) -> bool:
        return state_persistence.delete_published_agent(agent_id)
