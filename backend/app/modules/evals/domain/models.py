from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import EvalStatus


class EvalJobCreate(BaseModel):
    run_ids: list[UUID]
    dataset: str
    evaluators: list[str] = Field(default_factory=lambda: ["rule", "llm_judge", "tool_correctness"])


class EvalResult(BaseModel):
    sample_id: str
    run_id: UUID
    input: str
    status: str
    score: float
    reason: str | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvalJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    run_ids: list[UUID]
    dataset: str
    status: EvalStatus = EvalStatus.QUEUED
    results: list[EvalResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    failure_reason: str | None = None
