from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import RunStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvalJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringMode(str, Enum):
    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"


class SampleJudgement(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNSCORED = "unscored"
    RUNTIME_ERROR = "runtime_error"


class EvalJobCreateInput(BaseModel):
    agent_id: str
    dataset: str
    project: str
    tags: list[str] = Field(default_factory=list)
    scoring_mode: ScoringMode = ScoringMode.EXACT_MATCH


class EvalJobRecord(BaseModel):
    eval_job_id: UUID = Field(default_factory=uuid4)
    agent_id: str
    dataset: str
    project: str
    tags: list[str] = Field(default_factory=list)
    scoring_mode: ScoringMode
    status: EvalJobStatus = EvalJobStatus.QUEUED
    sample_count: int = 0
    scored_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unscored_count: int = 0
    runtime_error_count: int = 0
    pass_rate: float = 0.0
    failure_distribution: dict[str, int] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EvalSampleResult(BaseModel):
    eval_job_id: UUID
    dataset_sample_id: str
    run_id: UUID
    judgement: SampleJudgement
    input: str
    expected: str | None = None
    actual: str | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    tags: list[str] = Field(default_factory=list)


class EvalRunState(BaseModel):
    run_id: UUID
    dataset_sample_id: str
    status: RunStatus
    actual: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None
