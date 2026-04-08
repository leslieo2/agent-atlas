from __future__ import annotations

from typing import Any

from agent_atlas_contracts.runtime import ExecutionReferenceMetadata
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from app.modules.shared.domain.enums import ScoringMode

__all__ = [
    "EvaluatorConfig",
    "ExecutionBinding",
    "ExecutionProfile",
    "ExecutorResources",
    "ModelConfig",
    "PromptConfig",
    "ToolsetConfig",
    "build_source_artifact_ref",
    "build_source_execution_reference",
]


def build_source_artifact_ref(agent_id: str, source_fingerprint: str) -> str:
    return f"source://{agent_id}@{source_fingerprint}"


def build_source_execution_reference(
    *,
    agent_id: str,
    source_fingerprint: str,
) -> ExecutionReferenceMetadata:
    return ExecutionReferenceMetadata(
        artifact_ref=build_source_artifact_ref(agent_id, source_fingerprint),
        image_ref=None,
    )


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
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    backend: str
    tracing_backend: str = "state"
    execution_binding: SkipJsonSchema[ExecutionBinding | None] = Field(
        default=None,
        exclude=True,
        repr=False,
    )

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
