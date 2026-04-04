from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionTarget as ContractExecutionTarget
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ContractExecutionReferenceMetadata,
)
from agent_atlas_contracts.runtime import (
    TraceTelemetryMetadata as ContractTraceTelemetryMetadata,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.modules.shared.domain.enums import PolicyEffect, ScoringMode, StepType


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


class ExecutionReferenceMetadata(ContractExecutionReferenceMetadata):
    pass


def build_source_execution_reference(
    *,
    agent_id: str,
    source_fingerprint: str,
) -> ExecutionReferenceMetadata:
    return ExecutionReferenceMetadata(
        artifact_ref=build_source_artifact_ref(agent_id, source_fingerprint),
        image_ref=None,
    )


class ProvenanceMetadata(BaseModel):
    agent_family: str | None = None
    framework: str | None = None
    framework_version: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
    execution_target: ExecutionTarget | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    executor_backend: str | None = None
    trace_backend: str | None = None
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    approval_policy: ApprovalPolicySnapshot | None = None
    toolset: ToolsetConfig | None = None
    evaluator: EvaluatorConfig | None = None
    executor: ExecutorConfig | None = None


class TracingMetadata(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class ExecutionTarget(ContractExecutionTarget):
    pass


class TraceTelemetryMetadata(ContractTraceTelemetryMetadata):
    pass


class ToolPolicyRule(BaseModel):
    tool_name: str
    effect: PolicyEffect
    description: str | None = None


class ApprovalPolicySnapshot(BaseModel):
    approval_policy_id: UUID | None = None
    name: str | None = None
    tool_policies: list[ToolPolicyRule] = Field(default_factory=list)


class ModelConfig(BaseModel):
    model: str
    provider: str | None = None
    temperature: float = 0.0


class PromptConfig(BaseModel):
    prompt_template: str | None = None
    system_prompt: str | None = None
    prompt_version: str | None = None


class ToolsetConfig(BaseModel):
    tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluatorConfig(BaseModel):
    scoring_mode: ScoringMode = ScoringMode.EXACT_MATCH
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutorResources(BaseModel):
    cpu: str | None = None
    memory: str | None = None


class ExecutionBinding(BaseModel):
    runner_backend: str | None = None
    runner_image: str | None = None
    artifact_path: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ExecutionProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    backend: str
    tracing_backend: str = "state"
    execution_binding: SkipJsonSchema[ExecutionBinding | None] = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_executor_shape(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        payload = dict(value)
        binding_payload = payload.get("execution_binding") or payload.get("binding")
        binding = dict(binding_payload) if isinstance(binding_payload, dict) else {}
        binding_config = binding.get("config")
        config = dict(binding_config) if isinstance(binding_config, dict) else {}

        legacy_runner_backend = None
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            for key, item in metadata.items():
                config.setdefault(key, item)
            raw_runner_backend = metadata.get("runner_backend")
            if isinstance(raw_runner_backend, str) and raw_runner_backend.strip():
                legacy_runner_backend = raw_runner_backend

        if legacy_runner_backend is not None and "runner_backend" not in binding:
            binding["runner_backend"] = legacy_runner_backend

        for key in ("runner_image", "artifact_path"):
            if key in payload and key not in binding:
                binding[key] = payload[key]

        for key in ("timeout_seconds", "max_steps", "concurrency", "resources"):
            if key in payload and key not in config:
                config[key] = payload[key]

        if config:
            binding["config"] = config

        if binding:
            payload["execution_binding"] = binding

        for legacy_key in (
            "binding",
            "runner_image",
            "timeout_seconds",
            "max_steps",
            "concurrency",
            "resources",
            "artifact_path",
            "metadata",
        ):
            payload.pop(legacy_key, None)

        return payload

    @property
    def runner_image(self) -> str | None:
        return self.execution_binding.runner_image if self.execution_binding is not None else None

    @property
    def artifact_path(self) -> str | None:
        return self.execution_binding.artifact_path if self.execution_binding is not None else None

    @property
    def metadata(self) -> dict[str, Any]:
        if self.execution_binding is None:
            return {}
        return {
            key: value
            for key, value in self.execution_binding.config.items()
            if key not in {"timeout_seconds", "max_steps", "concurrency", "resources"}
        }

    @property
    def timeout_seconds(self) -> int:
        value = (
            self.execution_binding.config.get("timeout_seconds")
            if self.execution_binding is not None
            else None
        )
        return value if isinstance(value, int) else 600

    @property
    def max_steps(self) -> int:
        value = (
            self.execution_binding.config.get("max_steps")
            if self.execution_binding is not None
            else None
        )
        return value if isinstance(value, int) else 32

    @property
    def concurrency(self) -> int:
        value = (
            self.execution_binding.config.get("concurrency")
            if self.execution_binding is not None
            else None
        )
        return value if isinstance(value, int) else 1

    @property
    def resources(self) -> ExecutorResources:
        raw_resources = (
            self.execution_binding.config.get("resources")
            if self.execution_binding is not None
            else None
        )
        return ExecutorResources.model_validate(raw_resources or {})


ExecutorConfig = ExecutionProfile


class ExecutionProfileRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    backend: str
    tracing_backend: str = "state"

    def to_domain(self) -> tuple[ExecutorConfig, ExecutionBinding | None]:
        payload = self.model_dump(mode="python")
        payload.pop("binding", None)
        payload.pop("execution_binding", None)
        executor_config = ExecutorConfig.model_validate(payload)
        execution_binding = (
            executor_config.execution_binding.model_copy(deep=True)
            if executor_config.execution_binding is not None
            else None
        )
        public_profile = ExecutorConfig(
            backend=executor_config.backend,
            tracing_backend=executor_config.tracing_backend,
        )
        return public_profile, execution_binding


class TracePointer(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class TrajectoryStepRecord(BaseModel):
    id: str
    run_id: UUID
    step_type: StepType
    parent_step_id: str | None = None
    prompt: str
    output: str
    model: str | None = None
    temperature: float = 0.0
    latency_ms: int = 0
    token_usage: int = 0
    success: bool = True
    tool_name: str | None = None
    started_at: datetime = Field(default_factory=utc_now)


class RunLineage(BaseModel):
    experiment_id: UUID | None = None
    dataset_name: str | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    export_batch_ids: list[UUID] = Field(default_factory=list)
