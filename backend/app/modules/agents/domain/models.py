from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def compute_source_fingerprint(manifest: AgentManifest, entrypoint: str) -> str:
    payload = {
        "entrypoint": entrypoint,
        "manifest": manifest.model_dump(mode="json"),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AgentManifest(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: Literal["openai-agents-sdk"] = "openai-agents-sdk"
    default_model: str
    tags: list[str] = Field(default_factory=list)


class AgentBuildContext(BaseModel):
    run_id: UUID
    project: str
    dataset: str | None = None
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class AgentPublishState(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class AgentValidationIssue(BaseModel):
    code: str
    message: str


class PublishedAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    published_at: datetime = Field(default_factory=utc_now)
    source_fingerprint: str = ""

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

    def effective_source_fingerprint(self) -> str:
        if self.source_fingerprint:
            return self.source_fingerprint
        return compute_source_fingerprint(self.manifest, self.entrypoint)

    def to_snapshot(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"source_fingerprint"})


class DiscoveredAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    publish_state: AgentPublishState = AgentPublishState.DRAFT
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssue] = Field(default_factory=list)
    published_at: datetime | None = None
    last_validated_at: datetime = Field(default_factory=utc_now)
    has_unpublished_changes: bool = False

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
                }
            )
        return self.model_copy(
            update={
                "publish_state": AgentPublishState.PUBLISHED,
                "published_at": published_agent.published_at,
                "has_unpublished_changes": (
                    self.source_fingerprint() != published_agent.effective_source_fingerprint()
                ),
            }
        )

    def to_published(self) -> PublishedAgent:
        return PublishedAgent(
            manifest=self.manifest.model_copy(deep=True),
            entrypoint=self.entrypoint,
            source_fingerprint=self.source_fingerprint(),
        )
