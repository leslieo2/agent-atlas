from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.runtime import StepType
from agent_atlas_runner_langgraph.trace_mapper import build_trace_events_from_langgraph_run


def test_build_trace_events_from_langgraph_run_uses_last_message_output() -> None:
    result = {
        "messages": [
            {"response": "draft"},
            {"answer": "final answer"},
        ]
    }

    events = build_trace_events_from_langgraph_run(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        prompt="Summarize this report",
        model="gpt-5.4-mini",
        provider="langchain",
        result=result,
        token_usage=7,
        latency_ms=42,
    )

    assert len(events) == 1
    assert events[0].step_type is StepType.LLM
    assert events[0].input["prompt"] == "Summarize this report"
    assert events[0].output["output"] == "final answer"
    assert events[0].output["provider"] == "langchain"
    assert events[0].token_usage == 7

