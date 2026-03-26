from __future__ import annotations

from typing import Protocol

from app.modules.agents.domain.models import AgentDescriptor


class AgentCatalogPort(Protocol):
    def list_agents(self) -> list[AgentDescriptor]: ...

    def get_agent(self, agent_id: str) -> AgentDescriptor | None: ...
