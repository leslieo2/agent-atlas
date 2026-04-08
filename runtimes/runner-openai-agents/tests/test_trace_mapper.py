from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from agent_atlas_contracts.runtime import StepType
from agent_atlas_runner_openai_agents.trace_mapper import build_trace_events_from_agent_run


def test_build_trace_events_from_agent_run_threads_tool_outputs_into_follow_up_prompt() -> None:
    result = SimpleNamespace(
        raw_responses=[
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call-1",
                        name="lookup_customer",
                        arguments='{"customer_id":"123"}',
                    )
                ],
                usage=SimpleNamespace(total_tokens=3),
            ),
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="output_text", text="Customer loaded")],
                    )
                ],
                usage={"total_tokens": 2},
            ),
        ],
        new_items=[
            SimpleNamespace(
                output='{"status":"ok"}',
                raw_item={
                    "call_id": "call-1",
                    "type": "function_call_output",
                },
            )
        ],
    )

    events = build_trace_events_from_agent_run(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        prompt="Check the latest customer state",
        model="gpt-5.4-mini",
        provider="openai-agents-sdk",
        result=result,
    )

    assert [event.step_type for event in events] == [StepType.LLM, StepType.TOOL, StepType.LLM]
    assert events[0].output["output"].startswith("tool_call: lookup_customer")
    assert events[1].name == "lookup_customer"
    assert events[1].output == {"output": '{"status":"ok"}', "success": True}
    assert events[2].input["prompt"].endswith('Tool outputs:\nlookup_customer: {"status":"ok"}')
    assert events[2].output["output"] == "Customer loaded"


def test_build_trace_events_from_agent_run_marks_tool_failures() -> None:
    result = SimpleNamespace(
        raw_responses=[
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call-1",
                        name="lookup_customer",
                        arguments='{"customer_id":"123"}',
                    )
                ],
                usage={"total_tokens": 1},
            ),
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(type="output_text", text="Need another step")],
                    )
                ],
                usage={"total_tokens": 1},
            ),
        ],
        new_items=[
            SimpleNamespace(
                output="tool failed",
                raw_item={
                    "call_id": "call-1",
                    "type": "function_call_output",
                    "is_error": True,
                    "error": {"message": "permission denied"},
                },
            )
        ],
    )

    events = build_trace_events_from_agent_run(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        prompt="Check the latest customer state",
        model="gpt-5.4-mini",
        provider="openai-agents-sdk",
        result=result,
    )

    assert events[1].step_type is StepType.TOOL
    assert events[1].output["success"] is False
    assert events[1].output["error"] == "permission denied"
    assert events[2].output["success"] is False
    assert events[2].output["error"] == "permission denied"

