from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import StepType


class TraceIngestEvent(BaseModel):
    run_id: UUID
    span_id: str
    parent_span_id: str | None = None
    step_type: StepType = StepType.LLM
    name: str
    input: dict[str, Any]
    output: dict[str, Any] = Field(default_factory=dict)
    tool_name: str | None = None
    latency_ms: int = 0
    token_usage: int = 0
    image_digest: str | None = None
    prompt_version: str | None = None


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
    received_at: datetime = Field(default_factory=datetime.utcnow)
