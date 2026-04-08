from __future__ import annotations

from datetime import datetime

from agent_atlas_contracts.execution import ExecutionTarget
from agent_atlas_contracts.runtime import AgentManifest, ExecutionReferenceMetadata
from app.modules.agents.domain.models import (
    AgentValidationEvidenceSummary,
    AgentValidationIssue,
    AgentValidationOutcomeSummary,
    AgentValidationRunReference,
    GovernedPublishedAgent,
)
from app.modules.runs.adapters.inbound.http.schemas import build_run_create_input
from app.modules.runs.domain.models import RunCreateInput
from app.modules.shared.adapters.inbound.http.execution_profiles import ExecutionProfileRequest
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.execution import ExecutionProfile, ToolsetConfig
from app.modules.shared.domain.policies import ApprovalPolicySnapshot
from pydantic import BaseModel, ConfigDict, Field


class AgentDescriptorResponse(BaseModel):
    agent_id: str
    name: str
    description: str
    agent_family: str
    framework: str
    framework_version: str
    entrypoint: str
    default_model: str
    tags: list[str]
    capabilities: list[str]
    published_at: datetime
    source_fingerprint: str
    execution_reference: ExecutionReferenceMetadata
    default_runtime_profile: ExecutionProfile
    latest_validation: AgentValidationRunReferenceResponse | None = None
    validation_evidence: AgentValidationEvidenceSummaryResponse | None = None
    validation_outcome: AgentValidationOutcomeSummaryResponse | None = None

    @classmethod
    def from_domain(cls, agent: GovernedPublishedAgent) -> AgentDescriptorResponse:
        return cls(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            agent_family=agent.agent_family,
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


class AgentImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    name: str
    description: str
    framework: str
    default_model: str
    entrypoint: str
    agent_family: str | None = None
    framework_version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            agent_family=self.agent_family,
            framework=self.framework,
            framework_version=self.framework_version,
            default_model=self.default_model,
            tags=list(self.tags),
            capabilities=list(self.capabilities),
        )


class AgentValidationRunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    dataset: str | None = None
    input_summary: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    project_metadata: dict[str, object] = Field(default_factory=dict)
    execution_target: ExecutionTarget | None = None
    dataset_sample_id: str | None = None
    executor_config: ExecutionProfileRequest = Field(
        default_factory=lambda: ExecutionProfileRequest(backend=EXTERNAL_RUNNER_EXECUTION_BACKEND)
    )
    toolset_config: ToolsetConfig = Field(default_factory=ToolsetConfig)
    approval_policy: ApprovalPolicySnapshot | None = None

    def to_run_create_input(self, agent_id: str) -> RunCreateInput:
        tags = list(dict.fromkeys(["validation", *self.tags]))
        return build_run_create_input(
            project=self.project,
            dataset=self.dataset,
            agent_id=agent_id,
            input_summary=self.input_summary,
            prompt=self.prompt,
            tags=tags,
            project_metadata=dict(self.project_metadata),
            execution_target=self.execution_target,
            dataset_sample_id=self.dataset_sample_id,
            executor_config_request=self.executor_config,
            toolset_config=self.toolset_config.model_copy(deep=True),
            approval_policy=(
                self.approval_policy.model_copy(deep=True)
                if self.approval_policy is not None
                else None
            ),
        )
