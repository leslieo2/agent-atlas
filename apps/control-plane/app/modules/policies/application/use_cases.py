from __future__ import annotations

from app.modules.policies.application.ports import ApprovalPolicyRepository
from app.modules.policies.domain.models import ApprovalPolicyRecord


class PolicyQueries:
    def __init__(self, approval_policy_repository: ApprovalPolicyRepository) -> None:
        self.approval_policy_repository = approval_policy_repository

    def list(self) -> list[ApprovalPolicyRecord]:
        return self.approval_policy_repository.list()

    def get(self, approval_policy_id: str) -> ApprovalPolicyRecord | None:
        return self.approval_policy_repository.get(approval_policy_id)


class PolicyCommands:
    def __init__(self, approval_policy_repository: ApprovalPolicyRepository) -> None:
        self.approval_policy_repository = approval_policy_repository

    def create(self, payload: ApprovalPolicyRecord) -> ApprovalPolicyRecord:
        self.approval_policy_repository.save(payload)
        return payload
