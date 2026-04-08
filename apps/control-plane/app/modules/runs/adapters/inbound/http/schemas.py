from __future__ import annotations

from datetime import datetime
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionTarget
from pydantic import BaseModel, ConfigDict, Field

from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.adapters.inbound.http.execution_profiles import (
    ExecutionProfileRequest,
)
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.execution import ToolsetConfig
from app.modules.shared.domain.observability import RunLineage, TracePointer, TracingMetadata
from app.modules.shared.domain.policies import ApprovalPolicySnapshot
from app.modules.shared.domain.provenance import ProvenanceMetadata


def build_run_create_input(
    *,
    project: str,
    dataset: str | None,
    agent_id: str,
    input_summary: str,
    prompt: str,
    tags: list[str],
    project_metadata: dict[str, object],
    execution_target: ExecutionTarget | None,
    dataset_sample_id: str | None,
    executor_config_request: ExecutionProfileRequest,
    toolset_config: ToolsetConfig,
    approval_policy: ApprovalPolicySnapshot | None,
    experiment_id: UUID | None = None,
    dataset_version_id: UUID | None = None,
) -> RunCreateInput:
    executor_config, execution_binding = executor_config_request.to_domain()
    return RunCreateInput(
        experiment_id=experiment_id,
        dataset_version_id=dataset_version_id,
        project=project,
        dataset=dataset,
        agent_id=agent_id,
        input_summary=input_summary,
        prompt=prompt,
        tags=list(tags),
        project_metadata=dict(project_metadata),
        execution_target=(
            execution_target.model_copy(deep=True) if execution_target is not None else None
        ),
        dataset_sample_id=dataset_sample_id,
        executor_config=executor_config,
        execution_binding=execution_binding,
        toolset_config=toolset_config.model_copy(deep=True),
        approval_policy=(
            approval_policy.model_copy(deep=True) if approval_policy is not None else None
        ),
    )


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, object] = Field(default_factory=dict)
    execution_target: ExecutionTarget | None = None
    dataset_sample_id: str | None = None
    executor_config: ExecutionProfileRequest = Field(
        default_factory=lambda: ExecutionProfileRequest(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    approval_policy: ApprovalPolicySnapshot | None = None

    def to_domain(self) -> RunCreateInput:
        return build_run_create_input(
            experiment_id=self.experiment_id,
            dataset_version_id=self.dataset_version_id,
            project=self.project,
            dataset=self.dataset,
            agent_id=self.agent_id,
            input_summary=self.input_summary,
            prompt=self.prompt,
            tags=self.tags,
            project_metadata=self.project_metadata,
            execution_target=self.execution_target,
            dataset_sample_id=self.dataset_sample_id,
            executor_config_request=self.executor_config,
            toolset_config=self.toolset_config,
            approval_policy=self.approval_policy,
        )


class RunResponse(BaseModel):
    run_id: UUID
    attempt_id: UUID
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    input_summary: str
    status: RunStatus
    latency_ms: int
    token_cost: int
    tool_calls: int
    project: str
    dataset: str | None = None
    dataset_sample_id: str | None = None
    agent_id: str
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str]
    created_at: datetime
    project_metadata: dict[str, object]
    execution_target: ExecutionTarget | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    executor_submission_id: str | None = None
    attempt: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    runner_backend: str | None = None
    execution_backend: str | None = None
    container_image: str | None = None
    provenance: ProvenanceMetadata | None = None
    tracing: TracingMetadata | None = None
    trace_pointer: TracePointer | None = None
    lineage: RunLineage | None = None
    resolved_model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    termination_reason: str | None = None
    terminal_reason: str | None = None
    last_heartbeat_at: datetime | None = None
    last_progress_at: datetime | None = None
    lease_expires_at: datetime | None = None

    @classmethod
    def from_domain(cls, run: RunRecord) -> RunResponse:
        return cls.model_validate(run.model_dump(mode="json"))


class CancelRunResponse(BaseModel):
    run_id: UUID
    cancelled: bool
    status: RunStatus
    termination_reason: str | None = None
