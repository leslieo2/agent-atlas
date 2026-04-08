from __future__ import annotations

from app.modules.experiments.application.ports import ExperimentPolicyResolverPort
from app.modules.policies.application.ports import ApprovalPolicyRepository
from app.modules.shared.domain.models import ApprovalPolicySnapshot


class ApprovalPolicySnapshotResolver(ExperimentPolicyResolverPort):
    def __init__(self, approval_policy_repository: ApprovalPolicyRepository) -> None:
        self.approval_policy_repository = approval_policy_repository

    def resolve(self, approval_policy_id):
        policy = self.approval_policy_repository.get(approval_policy_id)
        if policy is None:
            return None
        return ApprovalPolicySnapshot(
            approval_policy_id=policy.approval_policy_id,
            name=policy.name,
            tool_policies=[rule.model_copy(deep=True) for rule in policy.tool_policies],
        )


__all__ = ["ApprovalPolicySnapshotResolver"]
