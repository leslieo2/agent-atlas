from __future__ import annotations

from pydantic import BaseModel

from app.modules.agents.domain.models import AgentDescriptor


class AgentDescriptorResponse(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    entrypoint: str
    default_model: str
    tags: list[str]

    @classmethod
    def from_domain(cls, agent: AgentDescriptor) -> AgentDescriptorResponse:
        return cls.model_validate(agent.model_dump())
