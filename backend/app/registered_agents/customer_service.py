from __future__ import annotations

from agents import Agent

from app.registered_agents.context import RegisteredAgentBuildContext


def build_agent(context: RegisteredAgentBuildContext) -> Agent[RegisteredAgentBuildContext]:
    del context
    return Agent(
        name="Customer Service Agent",
        instructions=(
            "You are a customer service specialist. "
            "Acknowledge the customer issue, provide the next action, "
            "and stay aligned with safe support policy."
        ),
    )
