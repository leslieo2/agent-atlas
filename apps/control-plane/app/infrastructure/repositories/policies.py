from __future__ import annotations

from uuid import UUID

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import (
    StatePersistenceSource,
    resolve_state_persistence,
    to_uuid,
)
from app.modules.policies.domain.models import ApprovalPolicyRecord


class StateApprovalPolicyRepository:
    def __init__(self, persistence: StatePersistenceSource = None) -> None:
        self._persistence_source = persistence

    @property
    def _persistence(self) -> StatePersistence:
        return resolve_state_persistence(self._persistence_source)

    def list(self) -> list[ApprovalPolicyRecord]:
        return self._persistence.list_approval_policies()

    def get(self, approval_policy_id: str | UUID) -> ApprovalPolicyRecord | None:
        return self._persistence.get_approval_policy(to_uuid(approval_policy_id))

    def save(self, policy: ApprovalPolicyRecord) -> None:
        self._persistence.save_approval_policy(policy)
