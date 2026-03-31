from __future__ import annotations

from datetime import datetime

from app.modules.agents.domain.models import (
    AgentPublishState,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)
from app.modules.shared.domain.models import ProvenanceMetadata, RuntimeArtifactMetadata
from pydantic import BaseModel


class AgentDescriptorResponse(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    framework_version: str
    entrypoint: str
    default_model: str
    tags: list[str]
    capabilities: list[str]
    published_at: datetime
    runtime_artifact: RuntimeArtifactMetadata | None = None
    provenance: ProvenanceMetadata | None = None

    @classmethod
    def from_domain(cls, agent: PublishedAgent) -> AgentDescriptorResponse:
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            framework=agent.framework,
            framework_version=agent.framework_version,
            entrypoint=agent.entrypoint,
            default_model=agent.default_model,
            tags=agent.tags,
            capabilities=agent.capabilities,
            published_at=agent.published_at,
            runtime_artifact=agent.runtime_artifact_or_raise(),
            provenance=agent.provenance,
        )


class AgentValidationIssueResponse(BaseModel):
    code: str
    message: str

    @classmethod
    def from_domain(cls, issue: AgentValidationIssue) -> AgentValidationIssueResponse:
        return cls.model_validate(issue.model_dump())


class DiscoveredAgentResponse(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    framework_version: str
    entrypoint: str
    default_model: str
    tags: list[str]
    capabilities: list[str]
    publish_state: AgentPublishState
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssueResponse]
    published_at: datetime | None = None
    last_validated_at: datetime
    has_unpublished_changes: bool
    runtime_artifact: RuntimeArtifactMetadata | None = None
    provenance: ProvenanceMetadata | None = None

    @classmethod
    def from_domain(cls, agent: DiscoveredAgent) -> DiscoveredAgentResponse:
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            framework=agent.framework,
            framework_version=agent.framework_version,
            entrypoint=agent.entrypoint,
            default_model=agent.default_model,
            tags=agent.tags,
            capabilities=agent.capabilities,
            publish_state=agent.publish_state,
            validation_status=agent.validation_status,
            validation_issues=[
                AgentValidationIssueResponse.from_domain(issue) for issue in agent.validation_issues
            ],
            published_at=agent.published_at,
            last_validated_at=agent.last_validated_at,
            has_unpublished_changes=agent.has_unpublished_changes,
            runtime_artifact=agent.runtime_artifact,
            provenance=agent.provenance,
        )


class AgentPublicationResponse(BaseModel):
    agent_id: str
    published: bool
