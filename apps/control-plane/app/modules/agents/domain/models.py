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
    PublishedAgent as ContractPublishedAgent,
)
from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import AdapterKind
from app.modules.shared.domain.models import (
    ProvenanceMetadata,
    RuntimeArtifactMetadata,
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
    provenance: ProvenanceMetadata | None = None

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
        return ["batch-execution", "phoenix-links", "offline-export"]

    def adapter_kind(self) -> AdapterKind:
        return adapter_kind_for_framework(self.framework)

    def runtime_artifact_or_raise(self) -> RuntimeArtifactMetadata:
        if self.runtime_artifact is None:
            raise ValueError(
                f"published agent '{self.agent_id}' is missing runtime artifact metadata"
            )

        runtime_artifact = RuntimeArtifactMetadata.model_validate(
            self.runtime_artifact.model_dump(mode="json")
        )
        required_fields = {
            "build_status": runtime_artifact.build_status,
            "source_fingerprint": runtime_artifact.source_fingerprint,
            "framework": runtime_artifact.framework,
            "entrypoint": runtime_artifact.entrypoint,
        }
        missing = [
            name
            for name, value in required_fields.items()
            if not isinstance(value, str) or not value
        ]
        if runtime_artifact.artifact_ref is None and runtime_artifact.image_ref is None:
            missing.append("artifact_ref|image_ref")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"published agent '{self.agent_id}' runtime artifact is incomplete: {joined}"
            )
        return runtime_artifact

    def to_snapshot(self) -> dict[str, Any]:
        snapshot = self.model_copy(
            update={"runtime_artifact": self.runtime_artifact_or_raise()},
            deep=True,
        )
        return snapshot.model_dump(mode="json", exclude={"provenance"})


class DiscoveredAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    publish_state: AgentPublishState = AgentPublishState.DRAFT
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssue] = Field(default_factory=list)
    published_at: datetime | None = None
    last_validated_at: datetime = Field(default_factory=utc_now)
    has_unpublished_changes: bool = False
    runtime_artifact: RuntimeArtifactMetadata | None = None
    provenance: ProvenanceMetadata | None = None

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
        return ["batch-execution", "phoenix-links", "offline-export"]

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
                    "runtime_artifact": None,
                    "provenance": None,
                }
            )
        return self.model_copy(
            update={
                "publish_state": AgentPublishState.PUBLISHED,
                "published_at": published_agent.published_at,
                "has_unpublished_changes": (
                    self.source_fingerprint()
                    != published_agent.runtime_artifact_or_raise().source_fingerprint
                ),
                "runtime_artifact": published_agent.runtime_artifact_or_raise(),
                "provenance": published_agent.provenance,
            }
        )

    def to_published(self) -> PublishedAgent:
        return PublishedAgent(
            manifest=self.manifest.model_copy(deep=True),
            entrypoint=self.entrypoint,
        )
