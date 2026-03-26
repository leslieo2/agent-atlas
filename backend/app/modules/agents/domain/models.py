from __future__ import annotations

from pydantic import BaseModel, Field


class AgentDescriptor(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    entrypoint: str
    default_model: str
    tags: list[str] = Field(default_factory=list)
