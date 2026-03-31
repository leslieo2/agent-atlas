from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.experiments.domain.models import (
    CandidateRunSummary,
    ExperimentCompareResult,
    ExperimentCompareSample,
    ExperimentCreateInput,
    ExperimentRecord,
    ExperimentRunDetail,
    ExperimentSpec,
    ExperimentStatus,
    RunEvaluationPatchInput,
)
from app.modules.shared.domain.enums import CompareOutcome, CurationStatus, SampleJudgement
from app.modules.shared.domain.models import (
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ToolsetConfig,
    TracingMetadata,
)


class ExperimentSpecRequest(BaseModel):
    dataset_version_id: UUID
    published_agent_id: str
    model_settings: ModelConfig
    prompt_config: PromptConfig = Field(default_factory=PromptConfig)
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig | None = None
    approval_policy_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)

    def to_domain(self) -> ExperimentSpec:
        return ExperimentSpec.model_validate(self.model_dump())


class ExperimentCreateRequest(BaseModel):
    name: str
    spec: ExperimentSpecRequest

    def to_domain(self) -> ExperimentCreateInput:
        return ExperimentCreateInput(name=self.name, spec=self.spec.to_domain())


class ExperimentResponse(BaseModel):
    experiment_id: UUID
    name: str
    dataset_name: str
    dataset_version_id: UUID
    published_agent_id: str
    status: ExperimentStatus
    tags: list[str]
    spec: ExperimentSpec
    sample_count: int
    completed_count: int
    passed_count: int
    failed_count: int
    unscored_count: int
    runtime_error_count: int
    pass_rate: float
    failure_distribution: dict[str, int]
    tracing: TracingMetadata | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_domain(cls, experiment: ExperimentRecord) -> ExperimentResponse:
        return cls.model_validate(experiment.model_dump(mode="json"))


class RunEvaluationPatchRequest(BaseModel):
    curation_status: CurationStatus | None = None
    curation_note: str | None = None
    export_eligible: bool | None = None

    def to_domain(self) -> RunEvaluationPatchInput:
        return RunEvaluationPatchInput.model_validate(self.model_dump())


class ExperimentRunResponse(BaseModel):
    run_id: UUID
    experiment_id: UUID
    dataset_sample_id: str
    input: str
    expected: str | None = None
    actual: str | None = None
    run_status: str
    judgement: SampleJudgement | None = None
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
    executor_backend: str | None = None
    latency_ms: int | None = None
    tool_calls: int | None = None
    trace_url: str | None = None

    @classmethod
    def from_domain(cls, detail: ExperimentRunDetail) -> ExperimentRunResponse:
        return cls.model_validate(detail.model_dump(mode="json"))


class CandidateRunSummaryResponse(BaseModel):
    run_id: UUID
    actual: str | None = None
    trace_url: str | None = None

    @classmethod
    def from_domain(cls, summary: CandidateRunSummary) -> CandidateRunSummaryResponse:
        return cls.model_validate(summary.model_dump(mode="json"))


class ExperimentCompareSampleResponse(BaseModel):
    dataset_sample_id: str
    baseline_judgement: SampleJudgement | None = None
    candidate_judgement: SampleJudgement | None = None
    compare_outcome: CompareOutcome
    error_code: str | None = None
    slice: str | None = None
    tags: list[str]
    candidate_run_summary: CandidateRunSummaryResponse | None = None

    @classmethod
    def from_domain(cls, sample: ExperimentCompareSample) -> ExperimentCompareSampleResponse:
        payload = sample.model_dump(mode="json")
        if sample.candidate_run_summary is not None:
            payload["candidate_run_summary"] = CandidateRunSummaryResponse.from_domain(
                sample.candidate_run_summary
            ).model_dump(mode="json")
        return cls.model_validate(payload)


class ExperimentCompareResponse(BaseModel):
    baseline_experiment_id: UUID
    candidate_experiment_id: UUID
    dataset_version_id: UUID
    distribution: dict[str, int]
    samples: list[ExperimentCompareSampleResponse]

    @classmethod
    def from_domain(cls, result: ExperimentCompareResult) -> ExperimentCompareResponse:
        return cls(
            baseline_experiment_id=result.baseline_experiment_id,
            candidate_experiment_id=result.candidate_experiment_id,
            dataset_version_id=result.dataset_version_id,
            distribution=result.distribution,
            samples=[
                ExperimentCompareSampleResponse.from_domain(sample) for sample in result.samples
            ],
        )
