from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.policies.application.use_cases import PolicyCommands, PolicyQueries


def get_policy_queries() -> PolicyQueries:
    return get_container().policies.policy_queries


def get_policy_commands() -> PolicyCommands:
    return get_container().policies.policy_commands
