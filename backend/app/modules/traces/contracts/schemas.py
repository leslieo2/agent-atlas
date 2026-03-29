from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.models import TraceTelemetryMetadata
from app.modules.traces.domain.models import TraceIngestEvent as DomainTraceIngestEvent
from app.modules.traces.domain.models import TraceSpan


class TraceSpanResponse(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None
    step_type: StepType
    input: dict[str, object]
    output: dict[str, object]
    tool_name: str | None = None
    latency_ms: int
    token_usage: int
    image_digest: str | None = None
    prompt_version: str | None = None
    trace_backend: str | None = None
    received_at: datetime

    @classmethod
    def from_domain(cls, span: TraceSpan) -> TraceSpanResponse:
        return cls.model_validate(span.model_dump())


class TraceIngestEvent(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None = None
    step_type: StepType = StepType.LLM
    name: str
    input: dict[str, object]
    output: dict[str, object] = Field(default_factory=dict)
    tool_name: str | None = None
    latency_ms: int = 0
    token_usage: int = 0
    image_digest: str | None = None
    prompt_version: str | None = None
    metadata: TraceTelemetryMetadata | None = None

    def to_domain(self) -> DomainTraceIngestEvent:
        return DomainTraceIngestEvent.model_validate(self.model_dump())
