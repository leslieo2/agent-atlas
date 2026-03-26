from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.infrastructure.adapters.traces import DefaultTraceProjector
from app.modules.shared.domain.enums import StepType
from app.modules.traces.domain.models import TraceIngestEvent, TraceSpan


def test_adapter_manager_normalizes_trace_event():
    run_id = uuid4()
    ingest_event = TraceIngestEvent(
        run_id=run_id,
        span_id="span-test",
        parent_span_id="parent-1",
        step_type=StepType.LLM,
        name="trace",
        input={"prompt": "Hello"},
        output={"output": "World"},
        tool_name="mock-tool",
        latency_ms=11,
        token_usage=22,
        image_digest="sha256:test",
        prompt_version="v1",
    )
    span = TraceSpan(
        run_id=run_id,
        span_id="span-test",
        parent_span_id="parent-1",
        step_type=StepType.LLM,
        input={"prompt": "Hello"},
        output={"output": "World"},
        tool_name="mock-tool",
        latency_ms=11,
        token_usage=22,
        image_digest="sha256:test",
        prompt_version="v1",
        received_at=datetime(2026, 3, 23, 12, 0, 0),
    )

    normalized = DefaultTraceProjector().normalize(event=ingest_event, span=span)

    assert normalized["run_id"] == str(run_id)
    assert normalized["span_id"] == "span-test"
    assert normalized["parent_span_id"] == "parent-1"
    assert normalized["step_type"] == "llm"
    assert normalized["input"] == {"prompt": "Hello"}
    assert normalized["output"] == {"output": "World"}
    assert normalized["tool_name"] == "mock-tool"
    assert normalized["latency_ms"] == 11
    assert normalized["token_usage"] == 22
    assert normalized["image_digest"] == "sha256:test"
    assert normalized["prompt_version"] == "v1"
    assert normalized["received_at"] == "2026-03-23T12:00:00"
