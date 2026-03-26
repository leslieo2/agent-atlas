from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RegisteredAgentDefinition(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: Literal["openai-agents-sdk"] = "openai-agents-sdk"
    entrypoint: str
    default_model: str
    tags: list[str] = Field(default_factory=list)


_REGISTRY: tuple[RegisteredAgentDefinition, ...] = (
    RegisteredAgentDefinition(
        agent_id="basic",
        name="Basic",
        description="Minimal registered agent for smoke testing the SDK execution path.",
        entrypoint="app.registered_agents.basic:build_agent",
        default_model="gpt-4.1-mini",
        tags=["example", "smoke"],
    ),
    RegisteredAgentDefinition(
        agent_id="customer_service",
        name="Customer Service",
        description=(
            "Customer-support style agent that responds with policy-aware " "service guidance."
        ),
        entrypoint="app.registered_agents.customer_service:build_agent",
        default_model="gpt-4.1-mini",
        tags=["example", "support"],
    ),
    RegisteredAgentDefinition(
        agent_id="tools",
        name="Tools",
        description=(
            "Example agent with local function tools for exercising " "registered tool execution."
        ),
        entrypoint="app.registered_agents.tools:build_agent",
        default_model="gpt-4.1-mini",
        tags=["example", "tools"],
    ),
)


def list_registered_agents() -> list[RegisteredAgentDefinition]:
    return [definition.model_copy(deep=True) for definition in _REGISTRY]


def get_registered_agent(agent_id: str) -> RegisteredAgentDefinition | None:
    for definition in _REGISTRY:
        if definition.agent_id == agent_id:
            return definition.model_copy(deep=True)
    return None
