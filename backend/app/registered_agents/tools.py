from __future__ import annotations

from agents import Agent, RunContextWrapper, function_tool

from app.registered_agents.context import RegisteredAgentBuildContext


@function_tool
def lookup_shipping_window(
    wrapper: RunContextWrapper[RegisteredAgentBuildContext],
    order_reference: str,
) -> str:
    dataset = wrapper.context.dataset or "prompt-only"
    priority = "priority" if "priority" in wrapper.context.tags else "standard"
    return (
        f"order={order_reference}; dataset={dataset}; "
        f"service_level={priority}; eta_window=2 business days"
    )


def build_agent(context: RegisteredAgentBuildContext) -> Agent[RegisteredAgentBuildContext]:
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
