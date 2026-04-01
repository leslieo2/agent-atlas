from __future__ import annotations

from typing import cast
from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import persistence, to_uuid
from app.modules.policies.domain.models import ApprovalPolicyRecord

state_persistence = cast(StatePersistence, persistence)


class StateApprovalPolicyRepository:
    def list(self) -> list[ApprovalPolicyRecord]:
        return state_persistence.list_approval_policies()

    def get(self, approval_policy_id: str | UUID) -> ApprovalPolicyRecord | None:
        return state_persistence.get_approval_policy(to_uuid(approval_policy_id))

    def save(self, policy: ApprovalPolicyRecord) -> None:
        state_persistence.save_approval_policy(policy)
