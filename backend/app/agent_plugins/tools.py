from __future__ import annotations

from agents import Agent, RunContextWrapper, function_tool

from app.modules.agents.domain.models import AgentBuildContext, AgentManifest

AGENT_MANIFEST = AgentManifest(
    agent_id="tools",
    name="Tools",
    description="Example agent with local function tools for exercising plugin tool execution.",
    default_model="gpt-4.1-mini",
    tags=["example", "tools"],
)


@function_tool
def lookup_shipping_window(
    wrapper: RunContextWrapper[AgentBuildContext],
    order_reference: str,
) -> str:
    dataset = wrapper.context.dataset or "prompt-only"
    priority = "priority" if "priority" in wrapper.context.tags else "standard"
    return (
        f"order={order_reference}; dataset={dataset}; "
        f"service_level={priority}; eta_window=2 business days"
    )


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Tools Agent",
        instructions=(
            "You are a shipping operations agent. "
            "When the user asks about shipping windows or order timing, "
            "use the available tools before answering."
        ),
        tools=[lookup_shipping_window],
    )
