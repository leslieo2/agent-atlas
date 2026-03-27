from __future__ import annotations

from typing import Final

from agents import Agent, ModelSettings, RunContextWrapper, function_tool

from app.core.errors import AppError
from app.modules.agents.domain.models import AgentBuildContext, AgentManifest

AGENT_MANIFEST = AgentManifest(
    agent_id="fulfillment_ops",
    name="Fulfillment Ops",
    description=(
        "Order-fulfillment validation agent that uses multiple local tools to decide "
        "the next customer-facing action."
    ),
    default_model="gpt-4.1-mini",
    tags=["example", "tools", "fulfillment"],
)


class ToolBackendError(AppError):
    code = "tool_backend_error"
    status_code = 502


ORDER_STATUS_FIXTURES: Final[dict[str, dict[str, str]]] = {
    "ORD-1001": {
        "status": "in_transit",
        "shipment_state": "carrier_scan",
        "sku": "SKU-ALPHA",
        "issue_type": "late_delivery",
        "priority": "standard",
        "reship_allowed": "no",
    },
    "ORD-1002": {
        "status": "lost_in_transit",
        "shipment_state": "exception",
        "sku": "SKU-ALPHA",
        "issue_type": "lost_package",
        "priority": "priority",
        "reship_allowed": "yes",
    },
    "ORD-1003": {
        "status": "awaiting_fulfillment",
        "shipment_state": "label_not_created",
        "sku": "SKU-BETA",
        "issue_type": "warehouse_delay",
        "priority": "standard",
        "reship_allowed": "no",
    },
    "ORD-1004": {
        "status": "delivered",
        "shipment_state": "proof_of_delivery",
        "sku": "SKU-GAMMA",
        "issue_type": "delivered_dispute",
        "priority": "standard",
        "reship_allowed": "no",
    },
}

INVENTORY_FIXTURES: Final[dict[str, dict[str, str]]] = {
    "SKU-ALPHA": {"stock_state": "in_stock", "replacement_available": "yes"},
    "SKU-BETA": {"stock_state": "out_of_stock", "replacement_available": "no"},
    "SKU-GAMMA": {"stock_state": "limited_stock", "replacement_available": "no"},
}

SHIPPING_WINDOW_FIXTURES: Final[dict[str, str]] = {
    "ORD-1001": "eta_window=2026-03-29 to 2026-03-30",
    "ORD-1002": "eta_window=unavailable_lost_in_transit",
    "ORD-1003": "eta_window=not_available_until_fulfillment",
    "ORD-1004": "eta_window=delivered_2026-03-25",
}

ESCALATION_POLICY_FIXTURES: Final[dict[tuple[str, str], str]] = {
    ("late_delivery", "standard"): "wait_for_delivery",
    ("lost_package", "priority"): "reship_order",
    ("warehouse_delay", "standard"): "escalate_to_human",
    ("delivered_dispute", "standard"): "escalate_to_human",
}


def _fail_if_injected(order_id: str) -> None:
    if order_id.startswith("ORD-ERR-"):
        raise ToolBackendError(
            f"tool backend unavailable for order '{order_id}'",
            order_id=order_id,
        )


def _format_fields(fields: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in fields.items())


def resolve_order_status(order_id: str) -> str:
    _fail_if_injected(order_id)
    record = ORDER_STATUS_FIXTURES.get(order_id)
    if record is None:
        raise ToolBackendError(
            f"order status lookup failed for order '{order_id}'",
            order_id=order_id,
        )
    return _format_fields({"order_id": order_id, **record})


def resolve_inventory(sku: str) -> str:
    record = INVENTORY_FIXTURES.get(sku)
    if record is None:
        raise ToolBackendError(f"inventory lookup failed for sku '{sku}'", sku=sku)
    return _format_fields({"sku": sku, **record})


def resolve_shipping_window(order_id: str) -> str:
    _fail_if_injected(order_id)
    window = SHIPPING_WINDOW_FIXTURES.get(order_id)
    if window is None:
        raise ToolBackendError(
            f"shipping window lookup failed for order '{order_id}'",
            order_id=order_id,
        )
    return f"order_id={order_id}; {window}"


def resolve_escalation_policy(issue_type: str, priority: str) -> str:
    action = ESCALATION_POLICY_FIXTURES.get((issue_type, priority))
    if action is None:
        raise ToolBackendError(
            "escalation policy lookup failed",
            issue_type=issue_type,
            priority=priority,
        )
    return f"issue_type={issue_type}; priority={priority}; recommended_action={action}"


@function_tool
def lookup_order_status(
    wrapper: RunContextWrapper[AgentBuildContext],
    order_id: str,
) -> str:
    del wrapper
    return resolve_order_status(order_id)


@function_tool
def lookup_inventory(
    wrapper: RunContextWrapper[AgentBuildContext],
    sku: str,
) -> str:
    del wrapper
    return resolve_inventory(sku)


@function_tool
def lookup_shipping_window(
    wrapper: RunContextWrapper[AgentBuildContext],
    order_id: str,
) -> str:
    del wrapper
    return resolve_shipping_window(order_id)


@function_tool
def lookup_escalation_policy(
    wrapper: RunContextWrapper[AgentBuildContext],
    issue_type: str,
    priority: str,
) -> str:
    del wrapper
    return resolve_escalation_policy(issue_type, priority)


def build_agent(context: AgentBuildContext) -> Agent[AgentBuildContext]:
    del context
    return Agent(
        name="Fulfillment Ops Agent",
        instructions=(
            "You are an order-fulfillment operations agent. "
            "You must identify the order issue, call the relevant tools, and then return "
            "exactly one line in the format 'resolved: <action>'. "
            "Use tools before answering whenever an order id, SKU, ETA, reshipment, or "
            "escalation decision is required. "
            "Preferred actions are: wait_for_delivery, reship_order, escalate_to_human. "
            "If the order is in transit and the shipping window is still active, return "
            "'resolved: wait_for_delivery'. "
            "If the order is lost in transit and replacement inventory is available, return "
            "'resolved: reship_order'. "
            "If inventory is unavailable, fulfillment is blocked, or the case is a delivered "
            "dispute, consult escalation policy and return 'resolved: escalate_to_human'. "
            "Do not include explanations, bullet points, or JSON."
        ),
        model_settings=ModelSettings(tool_choice="required"),
        tools=[
            lookup_order_status,
            lookup_inventory,
            lookup_shipping_window,
            lookup_escalation_policy,
        ],
    )
