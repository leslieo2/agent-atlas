from __future__ import annotations

from agents import Agent

from app.modules.agents.domain.models import AgentBuildContext, AgentManifest

AGENT_MANIFEST = AgentManifest(
    agent_id="customer_service",
    name="Customer Service",
    description="Customer-support style agent that responds with policy-aware service guidance.",
    default_model="gpt-4.1-mini",
    tags=["example", "support"],
)


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Customer Service Agent",
        instructions=(
            "You are a customer service specialist. "
            "Acknowledge the customer issue, provide the next action, "
            "and stay aligned with safe support policy."
        ),
    )
