from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import PolicyEffect


class ToolPolicyRule(BaseModel):
    tool_name: str
    effect: PolicyEffect
    description: str | None = None


class ApprovalPolicySnapshot(BaseModel):
    approval_policy_id: UUID | None = None
    name: str | None = None
    tool_policies: list[ToolPolicyRule] = Field(default_factory=list)
