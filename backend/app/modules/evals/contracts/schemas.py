from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.evals.domain.models import (
    CandidateRunSummary,
    CompareOutcome,
    CurationStatus,
    EvalCompareResult,
    EvalCompareSample,
    EvalJobCreateInput,
    EvalJobRecord,
    EvalJobStatus,
    EvalSamplePatchInput,
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
        return cls.model_validate(job.model_dump(mode="json"))


class EvalSamplePatchRequest(BaseModel):
    curation_status: CurationStatus | None = None
    curation_note: str | None = None
    export_eligible: bool | None = None

    def to_domain(self) -> EvalSamplePatchInput:
        return EvalSamplePatchInput.model_validate(self.model_dump())


class EvalSampleDetailResponse(BaseModel):
    eval_job_id: UUID
    dataset_sample_id: str
    run_id: UUID
    input: str
    expected: str | None = None
    actual: str | None = None
    judgement: SampleJudgement
    compare_outcome: CompareOutcome | None = None
    failure_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    tags: list[str]
    slice: str | None = None
    source: str | None = None
    export_eligible: bool | None = None
    curation_status: CurationStatus
    curation_note: str | None = None
    published_agent_snapshot: dict[str, object] | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
    phoenix_trace_url: str | None = None

    @classmethod
    def from_domain(
        cls,
        result: EvalSampleResult,
        *,
        compare_outcome: CompareOutcome | None = None,
    ) -> EvalSampleDetailResponse:
        payload = result.model_dump(mode="json")
        payload["compare_outcome"] = compare_outcome
        payload["phoenix_trace_url"] = payload.pop("trace_url", None)
        return cls.model_validate(payload)


class CandidateRunSummaryResponse(BaseModel):
    run_id: UUID
    actual: str | None = None
    trace_url: str | None = None

    @classmethod
    def from_domain(cls, summary: CandidateRunSummary) -> CandidateRunSummaryResponse:
        return cls.model_validate(summary.model_dump(mode="json"))


class EvalCompareSampleResponse(BaseModel):
    dataset_sample_id: str
    baseline_judgement: SampleJudgement | None = None
    candidate_judgement: SampleJudgement | None = None
    compare_outcome: CompareOutcome
    error_code: str | None = None
    slice: str | None = None
    tags: list[str]
    candidate_run_summary: CandidateRunSummaryResponse | None = None

    @classmethod
    def from_domain(cls, sample: EvalCompareSample) -> EvalCompareSampleResponse:
        payload = sample.model_dump(mode="json")
        if sample.candidate_run_summary is not None:
            payload["candidate_run_summary"] = CandidateRunSummaryResponse.from_domain(
                sample.candidate_run_summary
            ).model_dump(mode="json")
        return cls.model_validate(payload)


class EvalCompareResponse(BaseModel):
    baseline_eval_job_id: UUID
    candidate_eval_job_id: UUID
    dataset: str
    distribution: dict[str, int]
    samples: list[EvalCompareSampleResponse]

    @classmethod
    def from_domain(cls, result: EvalCompareResult) -> EvalCompareResponse:
        return cls(
            baseline_eval_job_id=result.baseline_eval_job_id,
            candidate_eval_job_id=result.candidate_eval_job_id,
            dataset=result.dataset,
            distribution=result.distribution,
            samples=[EvalCompareSampleResponse.from_domain(sample) for sample in result.samples],
        )
