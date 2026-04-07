from __future__ import annotations

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import resolve_state_persistence
from app.modules.agents.domain.models import PublishedAgent


class StatePublishedAgentRepository:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = resolve_state_persistence(persistence)

    def list_agents(self) -> list[PublishedAgent]:
        return self._persistence.list_published_agents()

    def get_agent(self, agent_id: str) -> PublishedAgent | None:
        return self._persistence.get_published_agent(agent_id)

    def save_agent(self, agent: PublishedAgent) -> None:
        self._persistence.save_published_agent(agent)

    def delete_agent(self, agent_id: str) -> bool:
        return self._persistence.delete_published_agent(agent_id)
