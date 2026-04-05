from __future__ import annotations

from agents import Agent
from app.modules.agents.domain.models import AgentBuildContext, AgentManifest
from app.modules.shared.domain.enums import AgentFamily

AGENT_MANIFEST = AgentManifest(
    agent_id="importable-basic",
    name="Importable Basic",
    description="Explicit source-import fixture agent for governed intake tests.",
    agent_family=AgentFamily.OPENAI_AGENTS.value,
    framework="openai-agents-sdk",
    default_model="gpt-5.4-mini",
    tags=["example", "import"],
)


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Importable Basic Agent",
        instructions="Answer directly and stay concise.",
    )
