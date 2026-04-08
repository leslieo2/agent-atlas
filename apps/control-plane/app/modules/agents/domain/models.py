from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from agent_atlas_contracts.runtime import (
    AgentBuildContext as AgentBuildContext,
)
from agent_atlas_contracts.runtime import (
    AgentManifest,
    ExecutionReferenceMetadata,
)
from agent_atlas_contracts.runtime import (
    PublishedAgent as ContractPublishedAgent,
)
from pydantic import BaseModel, Field

from app.modules.agents.domain.constants import CLAUDE_CODE_CLI_FRAMEWORK
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, AgentFamily, RunStatus
from app.modules.shared.domain.execution import (
    ExecutionBinding,
    ExecutionProfile,
    ExecutionTarget,
    ToolsetConfig,
)
from app.modules.shared.domain.observability import RunLineage, TracePointer, TracingMetadata
from app.modules.shared.domain.policies import ApprovalPolicySnapshot
from app.modules.shared.domain.provenance import ProvenanceMetadata


@dataclass(frozen=True)
class AgentModuleSource:
    module_name: str
    entrypoint: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def compute_source_fingerprint(manifest: AgentManifest, entrypoint: str) -> str:
    payload = {
        "entrypoint": entrypoint,
        "manifest": manifest.model_dump(mode="json"),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def agent_family_for_framework(framework: str) -> AgentFamily:
    normalized = framework.strip().lower()
    if normalized == AdapterKind.OPENAI_AGENTS.value:
        return AgentFamily.OPENAI_AGENTS
    if normalized == AdapterKind.LANGCHAIN.value:
        return AgentFamily.LANGCHAIN
    if normalized == AdapterKind.MCP.value:
        return AgentFamily.MCP
    if normalized == CLAUDE_CODE_CLI_FRAMEWORK:
        return AgentFamily.CLAUDE_CODE
    raise ValueError(f"unsupported published agent framework '{framework}'")


def adapter_kind_for_agent_family(agent_family: str) -> AdapterKind:
    normalized = agent_family.strip().lower()
    if normalized in {AgentFamily.OPENAI_AGENTS.value, AgentFamily.CLAUDE_CODE.value}:
        return AdapterKind.OPENAI_AGENTS
    if normalized == AgentFamily.LANGCHAIN.value:
        return AdapterKind.LANGCHAIN
    if normalized == AgentFamily.MCP.value:
        return AdapterKind.MCP
    raise ValueError(f"unsupported agent family '{agent_family}'")


def adapter_kind_for_framework(framework: str) -> AdapterKind:
    return adapter_kind_for_agent_family(agent_family_for_framework(framework).value)


class AgentValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class AgentValidationIssue(BaseModel):
    code: str
    message: str


class AgentValidationOutcomeStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    RUNNING = "running"


class AgentValidationRunReference(BaseModel):
    run_id: UUID
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AgentValidationRecord(BaseModel):
    agent_id: str
    run_id: UUID
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    terminal_summary: str | None = None


class AgentValidationRunCreateInput(BaseModel):
    project: str
    dataset: str | None = None
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    execution_target: ExecutionTarget | None = None
    dataset_sample_id: str | None = None
    executor_config: ExecutionProfile = Field(
        default_factory=lambda: ExecutionProfile(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    execution_binding: ExecutionBinding | None = None
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    approval_policy: ApprovalPolicySnapshot | None = None


class AgentValidationRun(BaseModel):
    run_id: UUID
    attempt_id: UUID
    input_summary: str
    status: RunStatus
    latency_ms: int = 0
    token_cost: int = 0
    tool_calls: int = 0
    project: str
    dataset: str | None = None
    dataset_sample_id: str | None = None
    agent_id: str
    model: str
    entrypoint: str | None = None
    agent_type: AdapterKind
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    project_metadata: dict[str, Any] = Field(default_factory=dict)
    execution_target: ExecutionTarget | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    executor_backend: str | None = None
    executor_submission_id: str | None = None
    attempt: int = 1
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


class AgentValidationEvidenceSummary(BaseModel):
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    terminal_summary: str | None = None


class AgentValidationOutcomeSummary(BaseModel):
    status: AgentValidationOutcomeStatus
    reason: str | None = None


PublishedAgentSnapshot = ContractPublishedAgent


def published_agent_snapshot(
    snapshot: Mapping[str, Any] | PublishedAgentSnapshot,
) -> PublishedAgentSnapshot:
    sealed = (
        snapshot
        if isinstance(snapshot, PublishedAgentSnapshot)
        else PublishedAgentSnapshot.model_validate(snapshot)
    )
    raw_family = sealed.manifest.agent_family
    if isinstance(raw_family, str) and raw_family.strip():
        return sealed
    return sealed.model_copy(
        update={
            "manifest": sealed.manifest.model_copy(
                update={"agent_family": agent_family_for_framework(sealed.framework).value},
                deep=True,
            )
        },
        deep=True,
    )


class PublishedAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    published_at: datetime = Field(default_factory=utc_now)
    source_fingerprint: str = ""
    execution_reference: ExecutionReferenceMetadata = Field(
        default_factory=ExecutionReferenceMetadata
    )
    default_runtime_profile: ExecutionProfile = Field(  # type: ignore[assignment]
        default_factory=lambda: ExecutionProfile(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    execution_binding: ExecutionBinding | None = None
    latest_validation: AgentValidationRunReference | None = None
    validation_evidence: AgentValidationEvidenceSummary | None = None
    validation_outcome: AgentValidationOutcomeSummary | None = None

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any] | PublishedAgentSnapshot) -> PublishedAgent:
        sealed = published_agent_snapshot(snapshot)
        return cls(
            manifest=sealed.manifest.model_copy(deep=True),
            entrypoint=sealed.entrypoint,
            published_at=sealed.published_at,
            source_fingerprint=sealed.source_fingerprint,
            execution_reference=sealed.execution_reference.model_copy(deep=True),
            default_runtime_profile=ExecutionProfile.model_validate(
                sealed.default_runtime_profile
            ),
        )

    @property
    def agent_id(self) -> str:
        return self.manifest.agent_id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def description(self) -> str:
        return self.manifest.description

    @property
    def framework(self) -> str:
        return self.manifest.framework

    @property
    def agent_family(self) -> str:
        raw_family = self.manifest.agent_family
        if isinstance(raw_family, str) and raw_family.strip():
            return raw_family
        return agent_family_for_framework(self.framework).value

    @property
    def default_model(self) -> str:
        return self.manifest.default_model

    @property
    def tags(self) -> list[str]:
        return list(self.manifest.tags)

    @property
    def framework_version(self) -> str:
        return self.manifest.framework_version

    @property
    def capabilities(self) -> list[str]:
        if self.manifest.capabilities:
            return list(self.manifest.capabilities)
        return ["external-runner-handoff", "phoenix-links", "offline-export"]

    def adapter_kind(self) -> AdapterKind:
        return adapter_kind_for_agent_family(self.agent_family)

    def source_fingerprint_or_raise(self) -> str:
        fingerprint = self.source_fingerprint.strip()
        if fingerprint:
            return fingerprint

        raise ValueError(
            f"published agent '{self.agent_id}' is missing source fingerprint metadata"
        )

    def execution_reference_or_raise(self) -> ExecutionReferenceMetadata:
        execution_reference = ExecutionReferenceMetadata.model_validate(self.execution_reference)
        artifact_ref = (
            execution_reference.artifact_ref.strip()
            if isinstance(execution_reference.artifact_ref, str)
            else ""
        )
        image_ref = (
            execution_reference.image_ref.strip()
            if isinstance(execution_reference.image_ref, str)
            else ""
        )
        if artifact_ref or image_ref:
            return execution_reference

        raise ValueError(
            f"published agent '{self.agent_id}' is missing execution reference metadata"
        )

    def to_snapshot(self) -> dict[str, Any]:
        return self.to_snapshot_model().model_dump(mode="json")

    def to_snapshot_model(self) -> PublishedAgentSnapshot:
        return PublishedAgentSnapshot(
            manifest=self.manifest.model_copy(deep=True),
            entrypoint=self.entrypoint,
            published_at=self.published_at,
            source_fingerprint=self.source_fingerprint_or_raise(),
            execution_reference=self.execution_reference_or_raise(),
            default_runtime_profile=self.default_runtime_profile.model_dump(
                mode="json",
                exclude_none=True,
            ),
        )


class DiscoveredAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssue] = Field(default_factory=list)
    last_validated_at: datetime = Field(default_factory=utc_now)
    default_runtime_profile: ExecutionProfile = Field(
        default_factory=lambda: ExecutionProfile(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    execution_binding: ExecutionBinding | None = None
    latest_validation: AgentValidationRunReference | None = None
    validation_evidence: AgentValidationEvidenceSummary | None = None
    validation_outcome: AgentValidationOutcomeSummary | None = None

    @property
    def agent_id(self) -> str:
        return self.manifest.agent_id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def description(self) -> str:
        return self.manifest.description

    @property
    def framework(self) -> str:
        return self.manifest.framework

    @property
    def agent_family(self) -> str:
        raw_family = self.manifest.agent_family
        if isinstance(raw_family, str) and raw_family.strip():
            return raw_family
        return agent_family_for_framework(self.framework).value

    @property
    def default_model(self) -> str:
        return self.manifest.default_model

    @property
    def tags(self) -> list[str]:
        return list(self.manifest.tags)

    @property
    def framework_version(self) -> str:
        return self.manifest.framework_version

    @property
    def capabilities(self) -> list[str]:
        if self.manifest.capabilities:
            return list(self.manifest.capabilities)
        return ["external-runner-handoff", "phoenix-links", "offline-export"]

    def adapter_kind(self) -> AdapterKind:
        return adapter_kind_for_agent_family(self.agent_family)

    def source_fingerprint(self) -> str:
        return compute_source_fingerprint(self.manifest, self.entrypoint)
