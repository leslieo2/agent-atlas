from __future__ import annotations

from agent_atlas_contracts.runtime import AgentBuildContext
from agents import Agent


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
