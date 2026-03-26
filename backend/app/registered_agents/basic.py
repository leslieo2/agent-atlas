from __future__ import annotations

from agents import Agent

from app.registered_agents.context import RegisteredAgentBuildContext


def build_agent(context: RegisteredAgentBuildContext) -> Agent[RegisteredAgentBuildContext]:
    del context
    return Agent(
        name="Basic Registered Agent",
        instructions=(
            "You are the basic registered agent used for execution smoke tests. "
            "Answer directly and stay concise."
        ),
    )
