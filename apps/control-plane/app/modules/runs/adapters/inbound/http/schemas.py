from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.runs.domain.models import RunCreateInput, RunRecord
from app.modules.shared.adapters.inbound.http.execution_profiles import (
    ExecutionProfileRequest,
)
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    ExecutionTarget,
    ProvenanceMetadata,
    RunLineage,
    ToolsetConfig,
    TracePointer,
    TracingMetadata,
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
        executor_config, execution_binding = self.executor_config.to_domain()
        payload = self.model_dump()
        payload["executor_config"] = executor_config.model_dump(mode="python")
        payload["execution_binding"] = (
            execution_binding.model_dump(mode="python") if execution_binding is not None else None
        )
        return RunCreateInput.model_validate(payload)


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
