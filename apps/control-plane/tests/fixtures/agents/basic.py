from __future__ import annotations

from agent_atlas_contracts.runtime import AgentBuildContext
from agents import Agent


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Basic Agent",
        instructions=(
            "You are the basic fixture agent used for execution smoke tests. "
            "Answer directly and stay concise."
        ),
    )
