from __future__ import annotations

from agent_atlas_contracts.runtime import AgentBuildContext
from agents import Agent


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Triage Bot",
        instructions=(
            "Classify the request, identify the next owner, and return a concise triage summary."
        ),
    )
