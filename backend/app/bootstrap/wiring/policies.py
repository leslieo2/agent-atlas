from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.policies.application.use_cases import PolicyCommands, PolicyQueries


@dataclass(frozen=True)
class PolicyModuleBundle:
    policy_queries: PolicyQueries
    policy_commands: PolicyCommands


def build_policy_module(infra: InfrastructureBundle) -> PolicyModuleBundle:
    policy_queries = PolicyQueries(approval_policy_repository=infra.approval_policy_repository)
    policy_commands = PolicyCommands(approval_policy_repository=infra.approval_policy_repository)
    return PolicyModuleBundle(
        policy_queries=policy_queries,
        policy_commands=policy_commands,
    )
