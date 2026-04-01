from __future__ import annotations

from datetime import datetime

from app.modules.agents.domain.models import (
    AgentPublishState,
    AgentValidationEvidenceSummary,
    AgentValidationIssue,
    AgentValidationOutcomeSummary,
    AgentValidationRunReference,
    AgentValidationStatus,
    DiscoveredAgent,
    ExecutionReference,
    PublishedAgent,
)
from app.modules.runs.domain.models import RunCreateInput
from app.modules.shared.domain.models import ApprovalPolicySnapshot, ExecutorConfig, ToolsetConfig
from pydantic import BaseModel, ConfigDict, Field


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
    latest_validation: AgentValidationRunReferenceResponse | None = None
    validation_evidence: AgentValidationEvidenceSummaryResponse | None = None
    validation_outcome: AgentValidationOutcomeSummaryResponse | None = None

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
            latest_validation=(
                AgentValidationRunReferenceResponse.from_domain(agent.latest_validation)
                if agent.latest_validation is not None
                else None
            ),
            validation_evidence=(
                AgentValidationEvidenceSummaryResponse.from_domain(agent.validation_evidence)
                if agent.validation_evidence is not None
                else None
            ),
            validation_outcome=(
                AgentValidationOutcomeSummaryResponse.from_domain(agent.validation_outcome)
                if agent.validation_outcome is not None
                else None
            ),
        )


class AgentValidationIssueResponse(BaseModel):
    code: str
    message: str

    @classmethod
    def from_domain(cls, issue: AgentValidationIssue) -> AgentValidationIssueResponse:
        return cls.model_validate(issue.model_dump())


class AgentValidationRunReferenceResponse(BaseModel):
    run_id: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_domain(
        cls, record: AgentValidationRunReference
    ) -> AgentValidationRunReferenceResponse:
        return cls.model_validate(record.model_dump(mode="json"))


class AgentValidationEvidenceSummaryResponse(BaseModel):
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    terminal_summary: str | None = None

    @classmethod
    def from_domain(
        cls, summary: AgentValidationEvidenceSummary
    ) -> AgentValidationEvidenceSummaryResponse:
        return cls.model_validate(summary.model_dump(mode="json"))


class AgentValidationOutcomeSummaryResponse(BaseModel):
    status: str
    reason: str | None = None

    @classmethod
    def from_domain(
        cls, summary: AgentValidationOutcomeSummary
    ) -> AgentValidationOutcomeSummaryResponse:
        return cls.model_validate(summary.model_dump(mode="json"))


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
    latest_validation: AgentValidationRunReferenceResponse | None = None
    validation_evidence: AgentValidationEvidenceSummaryResponse | None = None
    validation_outcome: AgentValidationOutcomeSummaryResponse | None = None

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
            latest_validation=(
                AgentValidationRunReferenceResponse.from_domain(agent.latest_validation)
                if agent.latest_validation is not None
                else None
            ),
            validation_evidence=(
                AgentValidationEvidenceSummaryResponse.from_domain(agent.validation_evidence)
                if agent.validation_evidence is not None
                else None
            ),
            validation_outcome=(
                AgentValidationOutcomeSummaryResponse.from_domain(agent.validation_outcome)
                if agent.validation_outcome is not None
                else None
            ),
        )


class AgentPublicationResponse(BaseModel):
    agent_id: str
    published: bool


class AgentValidationRunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    dataset: str | None = None
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, object] = Field(default_factory=dict)
    dataset_sample_id: str | None = None
    executor_config: ExecutorConfig = Field(
        default_factory=lambda: ExecutorConfig(backend="external-runner")
    )
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    approval_policy: ApprovalPolicySnapshot | None = None

    def to_domain(self, *, agent_id: str) -> RunCreateInput:
        tags = list(dict.fromkeys(["validation", *self.tags]))
        return RunCreateInput(
            project=self.project,
            dataset=self.dataset,
            agent_id=agent_id,
            input_summary=self.input_summary,
            prompt=self.prompt,
            tags=tags,
            project_metadata=dict(self.project_metadata),
            dataset_sample_id=self.dataset_sample_id,
            executor_config=self.executor_config.model_copy(deep=True),
            toolset_config=self.toolset_config.model_copy(deep=True),
            approval_policy=(
                self.approval_policy.model_copy(deep=True)
                if self.approval_policy is not None
                else None
            ),
        )
