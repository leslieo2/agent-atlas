from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from agent_atlas_contracts.runtime import (
    AgentBuildContext,
)
from agent_atlas_contracts.runtime import (
    AgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata,
)
from agent_atlas_contracts.runtime import (
    PublishedAgent as ContractPublishedAgent,
)
from pydantic import BaseModel, Field

from app.modules.agents.domain.constants import CLAUDE_CODE_CLI_FRAMEWORK
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, AgentFamily, RunStatus
from app.modules.shared.domain.execution import ExecutionBinding, ExecutionProfile


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


class AgentValidationEvidenceSummary(BaseModel):
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    terminal_summary: str | None = None


class AgentValidationOutcomeSummary(BaseModel):
    status: AgentValidationOutcomeStatus
    reason: str | None = None


class PublishedAgent(ContractPublishedAgent):
    manifest: AgentManifest
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
        snapshot = self.model_copy(
            update={
                "source_fingerprint": self.source_fingerprint_or_raise(),
                "execution_reference": self.execution_reference_or_raise(),
                "default_runtime_profile": self.default_runtime_profile.model_copy(deep=True),
            },
            deep=True,
        )
        return snapshot.model_dump(
            mode="json",
            exclude={"execution_binding"},
            exclude_none=True,
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
