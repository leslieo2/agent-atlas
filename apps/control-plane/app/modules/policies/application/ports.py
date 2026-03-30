from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.policies.domain.models import ApprovalPolicyRecord


class ApprovalPolicyRepository(Protocol):
    def list(self) -> list[ApprovalPolicyRecord]: ...

    def get(self, approval_policy_id: str | UUID) -> ApprovalPolicyRecord | None: ...

    def save(self, policy: ApprovalPolicyRecord) -> None: ...
