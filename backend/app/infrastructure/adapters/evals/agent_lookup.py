from __future__ import annotations

from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.evals.application.ports import AgentLookupPort


class RunnableAgentLookupAdapter(AgentLookupPort):
    def __init__(self, agent_catalog: RunnableAgentCatalogPort) -> None:
        self.agent_catalog = agent_catalog

    def exists(self, agent_id: str) -> bool:
        return self.agent_catalog.get_agent(agent_id) is not None
