from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.evals.domain.models import (
    EvalJobCreateInput,
    EvalJobRecord,
    EvalJobStatus,
    EvalSampleResult,
    SampleJudgement,
    ScoringMode,
)
from app.modules.shared.domain.models import ObservabilityMetadata


class EvalJobCreateRequest(BaseModel):
    agent_id: str
    dataset: str
    project: str
    tags: list[str] = Field(default_factory=list)
    scoring_mode: ScoringMode = ScoringMode.EXACT_MATCH

    def to_domain(self) -> EvalJobCreateInput:
        return EvalJobCreateInput.model_validate(self.model_dump())


class EvalJobResponse(BaseModel):
    eval_job_id: UUID
    agent_id: str
    dataset: str
    project: str
    tags: list[str]
    scoring_mode: ScoringMode
    status: EvalJobStatus
    sample_count: int
    scored_count: int
    passed_count: int
    failed_count: int
    unscored_count: int
    runtime_error_count: int
    pass_rate: float
    failure_distribution: dict[str, int]
    observability: ObservabilityMetadata | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_domain(cls, job: EvalJobRecord) -> EvalJobResponse:
        return cls.model_validate(job.model_dump())


class EvalSampleResultResponse(BaseModel):
    eval_job_id: UUID
    dataset_sample_id: str
    run_id: UUID
    judgement: SampleJudgement
    input: str
    expected: str | None = None
    actual: str | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    trace_url: str | None = None
    tags: list[str]

    @classmethod
    def from_domain(cls, result: EvalSampleResult) -> EvalSampleResultResponse:
        return cls.model_validate(result.model_dump())
