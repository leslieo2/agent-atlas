from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import PolicyEffect, ScoringMode


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


class RuntimeArtifactMetadata(BaseModel):
    build_status: str | None = None
    source_fingerprint: str | None = None
    framework: str | None = None
    entrypoint: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None


def build_source_runtime_artifact(
    *,
    agent_id: str,
    source_fingerprint: str,
    framework: str,
    entrypoint: str,
) -> RuntimeArtifactMetadata:
    return RuntimeArtifactMetadata(
        build_status="ready",
        source_fingerprint=source_fingerprint,
        framework=framework,
        entrypoint=entrypoint,
        artifact_ref=build_source_artifact_ref(agent_id, source_fingerprint),
        image_ref=None,
    )


class ProvenanceMetadata(BaseModel):
    framework: str | None = None
    framework_type: str | None = None
    framework_version: str | None = None
    published_agent_snapshot: dict[str, Any] | None = None
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


class ObservabilityMetadata(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class TraceTelemetryMetadata(BaseModel):
    agent_id: str | None = None
    framework: str | None = None
    framework_type: str | None = None
    framework_version: str | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    runner_backend: str | None = None
    executor_backend: str | None = None
    experiment_id: UUID | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    prompt_version: str | None = None
    image_digest: str | None = None


class RuntimeArtifactBuildResult(BaseModel):
    runtime_artifact: RuntimeArtifactMetadata
    provenance: ProvenanceMetadata


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


class ExecutorConfig(BaseModel):
    backend: str
    runner_image: str | None = None
    timeout_seconds: int = 600
    max_steps: int = 32
    concurrency: int = 1
    resources: ExecutorResources = Field(default_factory=ExecutorResources)
    tracing_backend: str = "phoenix"
    artifact_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TracePointer(BaseModel):
    backend: str
    trace_id: str | None = None
    trace_url: str | None = None
    project_url: str | None = None


class RunLineage(BaseModel):
    experiment_id: UUID | None = None
    dataset_name: str | None = None
    dataset_version_id: UUID | None = None
    dataset_sample_id: str | None = None
    export_batch_ids: list[UUID] = Field(default_factory=list)
