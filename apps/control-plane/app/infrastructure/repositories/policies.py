from __future__ import annotations

from uuid import UUID

from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.policies.domain.models import ApprovalPolicyRecord


class StateApprovalPolicyRepository:
    def list(self) -> list[ApprovalPolicyRecord]:
        return persistence.list_approval_policies()

    def get(self, approval_policy_id: str | UUID) -> ApprovalPolicyRecord | None:
        return persistence.get_approval_policy(to_uuid(approval_policy_id))

    def save(self, policy: ApprovalPolicyRecord) -> None:
        persistence.save_approval_policy(policy)
