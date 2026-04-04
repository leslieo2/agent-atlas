from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from agent_atlas_contracts.execution import (
    ExecutionArtifact,
    RunnerBootstrapPaths,
    RunnerRunSpec,
    TracingConfig,
    TracingExportConfig,
)
from pydantic import BaseModel, Field

from app.core.config import settings
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutionBinding,
    ExecutionTarget,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ProvenanceMetadata,
    ToolsetConfig,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExecutionCapability(BaseModel):
    backend: str
    production_ready: bool
    supports_cancel: bool
    supports_retry: bool
    supports_status: bool
    supports_heartbeat: bool


class RunHandle(BaseModel):
    run_id: UUID
    attempt_id: UUID = Field(default_factory=uuid4)
    backend: str
    executor_ref: str
    submitted_at: datetime = Field(default_factory=utc_now)


class CancelRequest(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    reason: str = "cancelled by user"


class Heartbeat(BaseModel):
    run_id: UUID
    attempt_id: UUID
    backend: str
    sequence: int
    status: RunStatus
    occurred_at: datetime = Field(default_factory=utc_now)
    lease_expires_at: datetime | None = None
    last_progress_at: datetime | None = None
    phase_hint: str | None = None


class RunTerminalSummary(BaseModel):
    run_id: UUID
    attempt_id: UUID
    status: RunStatus
    backend: str
    reason_code: str | None = None
    reason_message: str | None = None
    exit_code: int | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=utc_now)


class RunStatusSnapshot(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    backend: str | None = None
    executor_ref: str | None = None
    status: RunStatus
    reason_code: str | None = None
    reason_message: str | None = None
    heartbeat: Heartbeat | None = None
    terminal_summary: RunTerminalSummary | None = None


class ExecutionRunSpec(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    execution_target: ExecutionTarget | None = None
    dataset_sample_id: str | None = None
    model_settings: ModelConfig | None = None
    prompt_config: PromptConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    execution_binding: ExecutionBinding | None = None
    approval_policy: ApprovalPolicySnapshot | None = None
    provenance: ProvenanceMetadata | None = None


def _runner_tracing_config(trace_backend: str | None) -> TracingConfig | None:
    if not settings.tracing_otlp_endpoint:
        return None
    return TracingConfig(
        backend=trace_backend,
        project_name=settings.tracing_project_name,
        export=TracingExportConfig(
            endpoint=settings.tracing_otlp_endpoint,
            headers=dict(settings.tracing_headers),
        ),
    )


def runner_run_spec_from_run_spec(
    payload: ExecutionRunSpec,
    *,
    artifact: ExecutionArtifact,
    runner_backend: str,
    attempt: int = 1,
    attempt_id: UUID | None = None,
    bootstrap: RunnerBootstrapPaths | None = None,
) -> RunnerRunSpec:
    provenance = payload.provenance
    normalized_runner_backend = runner_backend.strip()
    if not normalized_runner_backend:
        raise ValueError("runner backend must be provided when building RunnerRunSpec")
    if artifact.framework is None or not artifact.framework.strip():
        raise ValueError("resolved execution artifact is missing framework")
    if artifact.entrypoint is None or not artifact.entrypoint.strip():
        raise ValueError("resolved execution artifact is missing entrypoint")
    if not artifact.published_agent_snapshot:
        raise ValueError("resolved execution artifact is missing published agent snapshot")
    executor_config = payload.executor_config.model_dump(mode="json")
    execution_binding = payload.execution_binding or payload.executor_config.execution_binding
    if execution_binding is not None:
        executor_config["binding"] = execution_binding.model_dump(mode="json", exclude_none=True)
    return RunnerRunSpec(
        run_id=payload.run_id,
        runner_backend=normalized_runner_backend,
        experiment_id=payload.experiment_id,
        dataset_version_id=payload.dataset_version_id,
        dataset_sample_id=payload.dataset_sample_id,
        attempt=attempt,
        attempt_id=attempt_id,
        project=payload.project,
        dataset=payload.dataset,
        agent_id=payload.agent_id,
        model=payload.model,
        entrypoint=artifact.entrypoint,
        agent_type=payload.agent_type.value,
        prompt=payload.prompt,
        tags=list(payload.tags),
        project_metadata=dict(payload.project_metadata),
        execution_target=(
            payload.execution_target.model_copy(deep=True)
            if payload.execution_target is not None
            else None
        ),
        executor_config=executor_config,
        agent_family=provenance.agent_family if provenance is not None else None,
        framework=artifact.framework,
        framework_type=provenance.agent_family if provenance is not None else None,
        artifact_ref=artifact.artifact_ref,
        image_ref=artifact.image_ref,
        trace_backend=provenance.trace_backend if provenance is not None else None,
        tracing=_runner_tracing_config(
            provenance.trace_backend if provenance is not None else None
        ),
        published_agent_snapshot=dict(artifact.published_agent_snapshot),
        bootstrap=bootstrap or RunnerBootstrapPaths(),
    )
