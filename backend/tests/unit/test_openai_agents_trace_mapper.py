from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from app.infrastructure.adapters.openai_agents.trace_mapper import (
    build_trace_events_from_agent_run,
)
from app.modules.shared.domain.enums import StepType


def test_build_trace_events_from_agent_run_expands_tool_calls():
    run_id = UUID("00000000-0000-0000-0000-000000000123")
    result = SimpleNamespace(
        raw_responses=[
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="lookup_shipping_window",
                        arguments='{"order_reference":"A-1024"}',
                        call_id="call-1",
                    )
                ],
                usage=SimpleNamespace(total_tokens=11),
            ),
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[
                            SimpleNamespace(type="output_text", text="ETA is 2 business days.")
                        ],
                    )
                ],
                usage=SimpleNamespace(total_tokens=17),
            ),
        ],
        new_items=[
            SimpleNamespace(
                raw_item={"call_id": "call-1", "output": "eta_window=2 business days"},
                output="eta_window=2 business days",
            )
        ],
    )

    events = build_trace_events_from_agent_run(
        run_id=run_id,
        prompt="Use the available tools to look up the shipping window for order A-1024.",
        model="gpt-5.4-mini",
        provider="openai-agents-sdk",
        result=result,
    )

    assert [event.step_type for event in events] == [StepType.LLM, StepType.TOOL, StepType.LLM]
    assert [event.span_id for event in events] == [
        f"span-{run_id}-1",
        f"span-{run_id}-2",
        f"span-{run_id}-3",
    ]
    assert events[1].parent_span_id == f"span-{run_id}-1"
    assert events[1].tool_name == "lookup_shipping_window"
    assert events[1].output["output"] == "eta_window=2 business days"
    assert events[1].output["success"] is True
    assert events[2].parent_span_id == f"span-{run_id}-2"
    assert events[2].token_usage == 17
    assert events[2].output["success"] is True


def test_build_trace_events_from_agent_run_marks_tool_backend_failures():
    run_id = UUID("00000000-0000-0000-0000-000000000124")
    result = SimpleNamespace(
        raw_responses=[
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="lookup_order_status",
                        arguments='{"order_id":"ORD-ERR-100"}',
                        call_id="call-err-1",
                    )
                ],
                usage=SimpleNamespace(total_tokens=9),
            ),
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="output_text", text="success")],
                    )
                ],
                usage=SimpleNamespace(total_tokens=4),
            ),
        ],
        new_items=[
            SimpleNamespace(
                raw_item={
                    "call_id": "call-err-1",
                    "output": (
                        "An error occurred while running the tool. Please try again. "
                        "Error: tool backend unavailable for order 'ORD-ERR-100'"
                    ),
                },
                output=(
                    "An error occurred while running the tool. Please try again. "
                    "Error: tool backend unavailable for order 'ORD-ERR-100'"
                ),
            )
        ],
    )

    events = build_trace_events_from_agent_run(
        run_id=run_id,
        prompt="Order ORD-ERR-100 is delayed. Check status and decide the next action.",
        model="gpt-5.4-mini",
        provider="openai-agents-sdk",
        result=result,
    )

    assert [event.step_type for event in events] == [StepType.LLM, StepType.TOOL, StepType.LLM]
    assert events[1].output["success"] is False
    assert events[1].output["error"] == "tool backend unavailable for order 'ORD-ERR-100'"
    assert events[2].output["success"] is False
    assert events[2].output["error"] == "tool backend unavailable for order 'ORD-ERR-100'"
