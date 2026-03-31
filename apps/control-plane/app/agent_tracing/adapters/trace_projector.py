from __future__ import annotations

from typing import Any

from app.agent_tracing.contracts import TraceProjectorPort
from app.modules.shared.domain.traces import TraceIngestEvent, TraceSpan


class TraceIngestProjector(TraceProjectorPort):
    def project(self, event: TraceIngestEvent) -> TraceSpan:
        return TraceSpan(
            run_id=event.run_id,
            span_id=event.span_id,
            parent_span_id=event.parent_span_id,
            step_type=event.step_type,
            input=event.input,
            output=event.output,
            tool_name=event.tool_name,
            latency_ms=event.latency_ms,
            token_usage=event.token_usage,
            image_digest=event.image_digest,
            prompt_version=event.prompt_version,
        )

    def normalize(
        self,
        span: TraceSpan,
        event: TraceIngestEvent | None = None,
    ) -> dict[str, Any]:
        return {
            "run_id": str(span.run_id),
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "step_type": span.step_type.value,
            "input": span.input,
            "output": span.output,
            "tool_name": span.tool_name,
            "latency_ms": span.latency_ms,
            "token_usage": span.token_usage,
            "image_digest": span.image_digest,
            "prompt_version": span.prompt_version,
            "trace_backend": span.trace_backend,
            "received_at": span.received_at.isoformat(),
        }
