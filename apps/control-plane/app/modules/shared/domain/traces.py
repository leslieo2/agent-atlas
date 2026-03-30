from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agent_atlas_contracts.runtime import TraceIngestEvent as ContractTraceIngestEvent
from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.models import TraceTelemetryMetadata


class TraceIngestEvent(ContractTraceIngestEvent):
    step_type: StepType = StepType.LLM
    metadata: TraceTelemetryMetadata | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


class TraceSpan(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None
    step_type: StepType
    input: dict[str, Any]
    output: dict[str, Any]
    tool_name: str | None = None
    latency_ms: int
    token_usage: int
    image_digest: str | None = None
    prompt_version: str | None = None
    trace_backend: str | None = None
    received_at: datetime = Field(default_factory=utc_now)
