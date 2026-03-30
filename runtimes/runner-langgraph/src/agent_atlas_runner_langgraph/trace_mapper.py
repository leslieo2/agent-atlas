from __future__ import annotations

import json
from typing import Any

from agent_atlas_contracts.runtime import StepType, TraceIngestEvent


def _stringify_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(value, dict):
        for key in ("output", "final_output", "answer", "response"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
        messages = value.get("messages")
        if isinstance(messages, list) and messages:
            return _stringify_output(messages[-1])
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if isinstance(value, list) and value:
        return _stringify_output(value[-1])
    return str(value)


def build_trace_events_from_langgraph_run(
    *,
    run_id: Any,
    prompt: str,
    model: str,
    provider: str,
    result: Any,
    token_usage: int,
    latency_ms: int,
) -> list[TraceIngestEvent]:
    return [
        TraceIngestEvent(
            run_id=run_id,
            span_id=f"span-{run_id}-1",
            step_type=StepType.LLM,
            name=model,
            input={
                "prompt": prompt,
                "model": model,
                "temperature": 0.0,
            },
            output={
                "output": _stringify_output(result),
                "success": True,
                "provider": provider,
            },
            latency_ms=latency_ms,
            token_usage=token_usage,
        )
    ]
