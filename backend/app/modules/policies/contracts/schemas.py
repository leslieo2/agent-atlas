from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.modules.policies.domain.models import ApprovalPolicyRecord
from app.modules.shared.domain.models import ToolPolicyRule
from pydantic import BaseModel, Field


class ApprovalPolicyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    tool_policies: list[ToolPolicyRule] = Field(default_factory=list)

    def to_domain(self) -> ApprovalPolicyRecord:
        return ApprovalPolicyRecord(
            name=self.name,
            description=self.description,
            tool_policies=[rule.model_copy(deep=True) for rule in self.tool_policies],
        )


class ApprovalPolicyResponse(BaseModel):
    approval_policy_id: UUID
    name: str
    description: str | None = None
    tool_policies: list[ToolPolicyRule]
    created_at: datetime

    @classmethod
    def from_domain(cls, policy: ApprovalPolicyRecord) -> ApprovalPolicyResponse:
        return cls.model_validate(policy.model_dump(mode="json"))
