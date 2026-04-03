from __future__ import annotations

from agents import Agent

from app.modules.agents.domain.models import AgentBuildContext


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Triage Bot",
        instructions=(
            "Classify the request, identify the next owner, and return a concise triage summary."
        ),
    )
