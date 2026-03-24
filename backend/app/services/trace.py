from __future__ import annotations

from app.db.state import state
from app.models.schemas import TraceIngestEvent, TraceSpan


class TraceGateway:
    def ingest(self, event: TraceIngestEvent) -> TraceSpan:
        span = TraceSpan(
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
        state.append_trace_span(span)
        return span


trace_gateway = TraceGateway()
