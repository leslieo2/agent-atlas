from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.models.schemas import AdapterKind, StepType, TraceSpan
from app.services.adapter import adapter_manager


def test_adapter_manager_normalizes_trace_event():
    run_id = uuid4()
    event = TraceSpan(
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

    normalized = adapter_manager.normalize_span(run_id=run_id, payload=event)

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


def test_adapter_manager_list_adapters():
    adapters = adapter_manager.list_adapters()

    kinds = [adapter.kind for adapter in adapters]
    assert len(adapters) == 3
    assert AdapterKind.OPENAI_AGENTS in kinds
    assert AdapterKind.LANGCHAIN in kinds
    assert AdapterKind.MCP in kinds
