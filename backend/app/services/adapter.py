from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.state import state
from app.models.schemas import AdapterDescriptor, TraceSpan


class AdapterManager:
    def list_adapters(self) -> list[AdapterDescriptor]:
        return list(state.adapters)

    def normalize_span(self, run_id: str | UUID, payload: TraceSpan) -> dict[str, Any]:
        # Basic normalization layer for adapter payloads coming from different runtimes.
        base = {
            "run_id": str(run_id),
            "span_id": payload.span_id,
            "parent_span_id": payload.parent_span_id,
            "step_type": payload.step_type.value,
            "input": payload.input,
            "output": payload.output,
            "tool_name": payload.tool_name,
            "latency_ms": payload.latency_ms,
            "token_usage": payload.token_usage,
            "image_digest": payload.image_digest,
            "prompt_version": payload.prompt_version,
            "received_at": payload.received_at.isoformat(),
        }
        return base


adapter_manager = AdapterManager()
