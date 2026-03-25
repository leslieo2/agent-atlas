from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.evals.domain.models import EvalJob, EvalResult
from app.modules.evals.domain.models import EvalJobCreate as DomainEvalJobCreate
from app.modules.shared.domain.enums import EvalStatus


class EvalJobCreate(BaseModel):
    run_ids: list[UUID]
    dataset: str
    evaluators: list[str] = Field(default_factory=lambda: ["rule", "llm_judge", "tool_correctness"])

    def to_domain(self) -> DomainEvalJobCreate:
        return DomainEvalJobCreate.model_validate(self.model_dump())


class EvalResultResponse(BaseModel):
    sample_id: str
    run_id: UUID
    input: str
    status: str
    score: float
    reason: str | None = None

    @classmethod
    def from_domain(cls, result: EvalResult) -> EvalResultResponse:
        return cls.model_validate(result.model_dump())


class EvalJobResponse(BaseModel):
    job_id: UUID
    run_ids: list[UUID]
    dataset: str
    status: EvalStatus
    results: list[EvalResultResponse]
    created_at: datetime
    failure_reason: str | None = None

    @classmethod
    def from_domain(cls, job: EvalJob) -> EvalJobResponse:
        payload = job.model_dump()
        payload["results"] = [EvalResultResponse.from_domain(result) for result in job.results]
        return cls.model_validate(payload)
