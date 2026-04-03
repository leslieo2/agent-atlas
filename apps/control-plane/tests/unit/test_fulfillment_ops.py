from __future__ import annotations

from uuid import UUID

import pytest
from agents import Agent
from app.modules.agents.domain.models import AgentBuildContext
from app.modules.agents.fixtures.fulfillment_ops import (
    ToolBackendError,
    build_agent,
    resolve_escalation_policy,
    resolve_inventory,
    resolve_order_status,
    resolve_shipping_window,
)


def test_fulfillment_ops_build_agent_returns_openai_agent() -> None:
    agent = build_agent(
        AgentBuildContext(
            run_id=UUID("00000000-0000-0000-0000-000000000000"),
            project="validation",
            dataset="fulfillment-eval-v1",
            prompt="validation",
            tags=[],
            project_metadata={},
        )
    )

    assert isinstance(agent, Agent)
    assert agent.name == "Fulfillment Ops Agent"
    assert getattr(agent.model_settings, "tool_choice", None) == "required"


def test_fulfillment_ops_resolvers_return_stable_payloads() -> None:
    assert (
        resolve_order_status("ORD-1002")
        == "order_id=ORD-1002; status=lost_in_transit; shipment_state=exception; "
        "sku=SKU-ALPHA; issue_type=lost_package; priority=priority; reship_allowed=yes"
    )
    assert (
        resolve_inventory("SKU-ALPHA")
        == "sku=SKU-ALPHA; stock_state=in_stock; replacement_available=yes"
    )
    assert (
        resolve_shipping_window("ORD-1001")
        == "order_id=ORD-1001; eta_window=2026-03-29 to 2026-03-30"
    )
    assert (
        resolve_escalation_policy("warehouse_delay", "standard")
        == "issue_type=warehouse_delay; priority=standard; recommended_action=escalate_to_human"
    )


def test_fulfillment_ops_failure_injection_raises_tool_backend_error() -> None:
    with pytest.raises(ToolBackendError) as exc:
        resolve_order_status("ORD-ERR-100")

    assert exc.value.code == "tool_backend_error"
    assert exc.value.message == "tool backend unavailable for order 'ORD-ERR-100'"
