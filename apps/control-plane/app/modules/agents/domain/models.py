from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from agent_atlas_contracts.runtime import (
    AgentBuildContext as ContractAgentBuildContext,
)
from agent_atlas_contracts.runtime import (
    AgentManifest as ContractAgentManifest,
)
from agent_atlas_contracts.runtime import (
    ExecutionReferenceMetadata as ContractExecutionReferenceMetadata,
)
from agent_atlas_contracts.runtime import (
    PublishedAgent as ContractPublishedAgent,
)
from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import (
    ExecutionReferenceMetadata as SharedExecutionReferenceMetadata,
)
from app.modules.shared.domain.models import (
    ExecutorConfig,
    build_source_execution_reference,
)


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


def adapter_kind_for_framework(framework: str) -> AdapterKind:
    normalized = framework.strip().lower()
    if normalized == AdapterKind.OPENAI_AGENTS.value:
        return AdapterKind.OPENAI_AGENTS
    if normalized == AdapterKind.LANGCHAIN.value:
        return AdapterKind.LANGCHAIN
    if normalized == AdapterKind.MCP.value:
        return AdapterKind.MCP
    raise ValueError(f"unsupported published agent framework '{framework}'")


class AgentManifest(ContractAgentManifest):
    pass


class AgentBuildContext(ContractAgentBuildContext):
    pass


class ExecutionReference(ContractExecutionReferenceMetadata):
    pass


class AgentValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class AgentPublishState(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class AgentValidationIssue(BaseModel):
    code: str
    message: str


class PublishedAgent(ContractPublishedAgent):
    manifest: AgentManifest
    execution_reference: ExecutionReference = Field(default_factory=ExecutionReference)
    default_runtime_profile: ExecutorConfig = Field(  # type: ignore[assignment]
        default_factory=lambda: ExecutorConfig(backend="external-runner")
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
        return adapter_kind_for_framework(self.framework)

    def source_fingerprint_or_raise(self) -> str:
        fingerprint = self.source_fingerprint.strip()
        if fingerprint:
            return fingerprint

        raise ValueError(
            f"published agent '{self.agent_id}' is missing source fingerprint metadata"
        )

    def execution_reference_or_raise(self) -> ExecutionReference:
        execution_reference = ExecutionReference.model_validate(self.execution_reference)
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
        return snapshot.model_dump(mode="json", exclude_none=True)


class DiscoveredAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    publish_state: AgentPublishState = AgentPublishState.DRAFT
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssue] = Field(default_factory=list)
    published_at: datetime | None = None
    last_validated_at: datetime = Field(default_factory=utc_now)
    has_unpublished_changes: bool = False
    execution_reference: SharedExecutionReferenceMetadata | None = None
    default_runtime_profile: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="external-runner")
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
        return adapter_kind_for_framework(self.framework)

    def with_publish_state(self, publish_state: AgentPublishState) -> DiscoveredAgent:
        return self.model_copy(update={"publish_state": publish_state})

    def source_fingerprint(self) -> str:
        return compute_source_fingerprint(self.manifest, self.entrypoint)

    def with_publication(self, published_agent: PublishedAgent | None) -> DiscoveredAgent:
        if published_agent is None:
            return self.model_copy(
                update={
                    "publish_state": AgentPublishState.DRAFT,
                    "published_at": None,
                    "has_unpublished_changes": False,
                    "execution_reference": None,
                }
            )
        return self.model_copy(
            update={
                "publish_state": AgentPublishState.PUBLISHED,
                "published_at": published_agent.published_at,
                "has_unpublished_changes": (
                    self.source_fingerprint() != published_agent.source_fingerprint_or_raise()
                ),
                "execution_reference": published_agent.execution_reference_or_raise(),
                "default_runtime_profile": published_agent.default_runtime_profile.model_copy(
                    deep=True
                ),
            }
        )

    def to_published(self, existing: PublishedAgent | None = None) -> PublishedAgent:
        source_fingerprint = self.source_fingerprint()
        default_runtime_profile = (
            existing.default_runtime_profile.model_copy(deep=True)
            if existing is not None
            else self.default_runtime_profile.model_copy(deep=True)
        )
        return PublishedAgent(
            manifest=self.manifest.model_copy(deep=True),
            entrypoint=self.entrypoint,
            source_fingerprint=source_fingerprint,
            execution_reference=ExecutionReference.model_validate(
                build_source_execution_reference(
                    agent_id=self.agent_id,
                    source_fingerprint=source_fingerprint,
                ).model_dump(mode="json")
            ),
            default_runtime_profile=default_runtime_profile,
        )
