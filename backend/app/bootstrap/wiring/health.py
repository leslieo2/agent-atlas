from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.wiring.infrastructure import InfrastructureBundle
from app.modules.health.application.use_cases import HealthQueries


@dataclass(frozen=True)
class HealthModuleBundle:
    health_queries: HealthQueries


def build_health_module(infra: InfrastructureBundle) -> HealthModuleBundle:
    return HealthModuleBundle(
        health_queries=HealthQueries(system_status=infra.system_status),
    )
