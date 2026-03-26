from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


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


class DiscoveredAgent(BaseModel):
    manifest: AgentManifest
    entrypoint: str
    publish_state: AgentPublishState = AgentPublishState.DRAFT
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssue] = Field(default_factory=list)

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

    def to_published(self) -> PublishedAgent:
        return PublishedAgent(
            manifest=self.manifest.model_copy(deep=True),
            entrypoint=self.entrypoint,
        )
