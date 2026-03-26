from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.modules.agents.domain.models import (
    AgentPublishState,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
    PublishedAgent,
)


class AgentDescriptorResponse(BaseModel):
    agent_id: str
    name: str
    description: str
    framework: str
    entrypoint: str
    default_model: str
    tags: list[str]
    published_at: datetime

    @classmethod
    def from_domain(cls, agent: PublishedAgent) -> AgentDescriptorResponse:
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            framework=agent.framework,
            entrypoint=agent.entrypoint,
            default_model=agent.default_model,
            tags=agent.tags,
            published_at=agent.published_at,
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
    entrypoint: str
    default_model: str
    tags: list[str]
    publish_state: AgentPublishState
    validation_status: AgentValidationStatus
    validation_issues: list[AgentValidationIssueResponse]

    @classmethod
    def from_domain(cls, agent: DiscoveredAgent) -> DiscoveredAgentResponse:
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            framework=agent.framework,
            entrypoint=agent.entrypoint,
            default_model=agent.default_model,
            tags=agent.tags,
            publish_state=agent.publish_state,
            validation_status=agent.validation_status,
            validation_issues=[
                AgentValidationIssueResponse.from_domain(issue) for issue in agent.validation_issues
            ],
        )


class AgentPublicationResponse(BaseModel):
    agent_id: str
    published: bool
