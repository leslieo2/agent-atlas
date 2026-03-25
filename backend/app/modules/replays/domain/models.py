from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReplayRequest(BaseModel):
    run_id: UUID
    step_id: str
    edited_prompt: str | None = None
    model: str | None = None
    tool_overrides: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReplayResult(BaseModel):
    replay_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_id: str
    baseline_output: str
    replay_output: str
    diff: str
    updated_prompt: str | None
    model: str
    temperature: float = 0.0
    started_at: datetime = Field(default_factory=utc_now)
