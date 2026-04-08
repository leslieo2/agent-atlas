from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.modules.agents.domain.models import GovernedPublishedAgent
from app.modules.experiments.domain.models import (
    ExperimentRecord,
    ExperimentRunDetail,
    RunEvaluationRecord,
)
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    TracePointer,
    TrajectoryStepRecord,
)
from app.modules.shared.domain.provenance import ProvenanceMetadata
from pydantic import BaseModel, Field


class ExperimentRepository(Protocol):
    def list(self) -> list[ExperimentRecord]: ...

    def get(self, experiment_id: str | UUID) -> ExperimentRecord | None: ...

    def save(self, experiment: ExperimentRecord) -> None: ...


class RunEvaluationRepository(Protocol):
    def list_for_experiment(self, experiment_id: str | UUID) -> list[RunEvaluationRecord]: ...

    def get_by_run(self, run_id: str | UUID) -> RunEvaluationRecord | None: ...

    def save(self, record: RunEvaluationRecord) -> None: ...

    def delete_for_experiment(self, experiment_id: str | UUID) -> None: ...


class ExperimentSampleExecution(BaseModel):
    dataset_version_id: UUID
    dataset_name: str
    dataset_sample_id: str
    input: str
    expected: str | None = None
    tags: list[str] = Field(default_factory=list)
    slice: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None
    export_eligible: bool | None = None


class ExperimentRunRef(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    dataset_sample_id: str | None = None
    status: RunStatus


class ExperimentAggregationRun(BaseModel):
    run_id: UUID
    dataset_sample_id: str | None = None
    status: RunStatus
    created_at: datetime
    error_message: str | None = None
    termination_reason: str | None = None
    error_code: str | None = None
    trace_pointer: TracePointer | None = None
    provenance: ProvenanceMetadata | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    latency_ms: int = 0
    tool_calls: int = 0
    container_image: str | None = None


class ExperimentPolicyResolverPort(Protocol):
    def resolve(self, approval_policy_id: str | UUID) -> ApprovalPolicySnapshot | None: ...


class ExperimentRunLauncherPort(Protocol):
    def launch(
        self,
        experiment: ExperimentRecord,
        sample: ExperimentSampleExecution,
        agent: GovernedPublishedAgent,
    ) -> None: ...


class ExperimentRunLookupPort(Protocol):
    def list_for_experiment(self, experiment_id: str | UUID) -> list[ExperimentRunRef]: ...


class ExperimentRunQueryPort(Protocol):
    def list_details(self, experiment: ExperimentRecord) -> list[ExperimentRunDetail]: ...


class ExperimentAggregationLookupPort(Protocol):
    def list_runs(self, experiment_id: str | UUID) -> list[ExperimentAggregationRun]: ...


class ExperimentTrajectoryLookupPort(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStepRecord]: ...


__all__ = [
    "ExperimentAggregationLookupPort",
    "ExperimentAggregationRun",
    "ExperimentPolicyResolverPort",
    "ExperimentRepository",
    "ExperimentRunLauncherPort",
    "ExperimentRunLookupPort",
    "ExperimentRunQueryPort",
    "ExperimentRunRef",
    "ExperimentSampleExecution",
    "ExperimentTrajectoryLookupPort",
    "RunEvaluationRepository",
]
