from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from agent_atlas_contracts.runtime import RuntimeExecutionResult as SharedRuntimeExecutionResult
from pydantic import BaseModel, ConfigDict, Field

from app.execution.contracts import ExecutionRunSpec
from app.modules.shared.domain.enums import AdapterKind, RunStatus
from app.modules.shared.domain.models import (
    ApprovalPolicySnapshot,
    EvaluatorConfig,
    ExecutorConfig,
    ModelConfig,
    PromptConfig,
    ProvenanceMetadata,
    RunLineage,
    ToolsetConfig,
    TracePointer,
    TracingMetadata,
    TrajectoryStepRecord,
    utc_now,
)

DEFAULT_EXECUTION_BACKEND = "external-runner"


class RunCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    project: str
    dataset: str | None = None
    agent_id: str
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="external-runner")
    )
    model_settings: ModelConfig | None = None
    prompt_config: PromptConfig | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    evaluator_config: EvaluatorConfig = Field(default_factory=EvaluatorConfig)
    approval_policy: ApprovalPolicySnapshot | None = None


class ExecutionMetrics(BaseModel):
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0


RuntimeExecutionResult = SharedRuntimeExecutionResult


class RunRecord(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    attempt_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    input_summary: str
    status: RunStatus = RunStatus.QUEUED
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0
    project: str
    dataset: str | None = None
    dataset_sample_id: str | None = None
    agent_id: str = ""
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    executor_submission_id: str | None = None
    attempt: int = 1
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
    heartbeat_sequence: int = 0

    def to_run_spec(self) -> ExecutionRunSpec:
        prompt = str(self.project_metadata.get("prompt", ""))
        project_metadata = dict(self.project_metadata)
        project_metadata.pop("prompt", None)
        provenance = self.provenance.model_copy(deep=True) if self.provenance is not None else None
        prompt_version = project_metadata.get("prompt_version")
        system_prompt = project_metadata.get("system_prompt")
        model_settings = None
        prompt_config = None
        toolset_config = ToolsetConfig()
        evaluator_config = EvaluatorConfig()
        executor_config = ExecutorConfig(backend=self.executor_backend or DEFAULT_EXECUTION_BACKEND)
        approval_policy = None
        if provenance is not None:
            model_settings = ModelConfig(model=self.resolved_model or self.model)
            prompt_config = PromptConfig(
                prompt_version=prompt_version if isinstance(prompt_version, str) else None,
                system_prompt=system_prompt if isinstance(system_prompt, str) else None,
            )
            toolset_config = (
                provenance.toolset.model_copy(deep=True)
                if provenance.toolset is not None
                else ToolsetConfig()
            )
            evaluator_config = (
                provenance.evaluator.model_copy(deep=True)
                if provenance.evaluator is not None
                else EvaluatorConfig()
            )
            executor_config = (
                provenance.executor.model_copy(deep=True)
                if provenance.executor is not None
                else ExecutorConfig(backend=self.executor_backend or DEFAULT_EXECUTION_BACKEND)
            )
            approval_policy = (
                provenance.approval_policy.model_copy(deep=True)
                if provenance.approval_policy is not None
                else None
            )
            provenance = provenance.model_copy(
                update={
                    "artifact_ref": self.artifact_ref,
                    "image_ref": self.image_ref,
                    "executor_backend": self.executor_backend,
                }
            )

        return ExecutionRunSpec(
            run_id=self.run_id,
            experiment_id=self.experiment_id,
            dataset_version_id=self.dataset_version_id,
            project=self.project,
            dataset=self.dataset,
            agent_id=self.agent_id,
            model=self.resolved_model or self.model,
            entrypoint=self.entrypoint,
            agent_type=self.agent_type,
            input_summary=self.input_summary,
            prompt=prompt,
            tags=list(self.tags),
            project_metadata=project_metadata,
            dataset_sample_id=self.dataset_sample_id,
            model_settings=model_settings,
            prompt_config=prompt_config,
            toolset_config=toolset_config,
            evaluator_config=evaluator_config,
            executor_config=executor_config,
            approval_policy=approval_policy,
            provenance=provenance,
        )


TrajectoryStep = TrajectoryStepRecord
