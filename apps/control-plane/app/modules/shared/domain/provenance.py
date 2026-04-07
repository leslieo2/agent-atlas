from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionTarget
from pydantic import BaseModel

from app.modules.shared.domain.execution import (
    EvaluatorConfig,
    ExecutionProfile,
    ToolsetConfig,
)
from app.modules.shared.domain.policies import ApprovalPolicySnapshot


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
    executor: ExecutionProfile | None = None
