from __future__ import annotations

from app.modules.agents.application.ports import AgentCatalogPort
from app.modules.agents.domain.models import AgentDescriptor


class AgentQueries:
    def __init__(self, agent_catalog: AgentCatalogPort) -> None:
        self.agent_catalog = agent_catalog

    def list_agents(self) -> list[AgentDescriptor]:
        return self.agent_catalog.list_agents()
