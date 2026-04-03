from __future__ import annotations

from agents import Agent

from app.modules.agents.domain.models import AgentBuildContext


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Basic Agent",
        instructions=(
            "You are the basic fixture agent used for execution smoke tests. "
            "Answer directly and stay concise."
        ),
    )
