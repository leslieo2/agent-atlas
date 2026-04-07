from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.shared.domain.policies import ToolPolicyRule
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalPolicyRecord(BaseModel):
    approval_policy_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    tool_policies: list[ToolPolicyRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
