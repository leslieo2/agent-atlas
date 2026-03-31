from __future__ import annotations

from datetime import datetime

from app.modules.agents.domain.models import (
    AgentPublishState,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    ExecutionReference,
    PublishedAgent,
)
from app.modules.shared.domain.models import ExecutorConfig
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
    source_fingerprint: str
    execution_reference: ExecutionReference
    default_runtime_profile: ExecutorConfig

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
            source_fingerprint=agent.source_fingerprint_or_raise(),
            execution_reference=agent.execution_reference_or_raise(),
            default_runtime_profile=agent.default_runtime_profile.model_copy(deep=True),
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
    source_fingerprint: str
    execution_reference: ExecutionReference | None = None
    default_runtime_profile: ExecutorConfig

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
            source_fingerprint=agent.source_fingerprint(),
            execution_reference=(
                ExecutionReference.model_validate(agent.execution_reference.model_dump(mode="json"))
                if agent.execution_reference is not None
                else None
            ),
            default_runtime_profile=agent.default_runtime_profile.model_copy(deep=True),
        )


class AgentPublicationResponse(BaseModel):
    agent_id: str
    published: bool
