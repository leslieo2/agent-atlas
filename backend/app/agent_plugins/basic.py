from __future__ import annotations

from agents import Agent

from app.modules.agents.domain.models import AgentBuildContext, AgentManifest

AGENT_MANIFEST = AgentManifest(
    agent_id="basic",
    name="Basic",
    description="Minimal plugin agent for smoke testing the SDK execution path.",
    default_model="gpt-4.1-mini",
    tags=["example", "smoke"],
)


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Basic Agent",
        instructions=(
            "You are the basic plugin agent used for execution smoke tests. "
            "Answer directly and stay concise."
        ),
    )
