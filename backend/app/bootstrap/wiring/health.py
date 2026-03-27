from __future__ import annotations

from app.bootstrap.bundles import HealthModuleBundle, InfrastructureBundle
from app.modules.health.application.use_cases import HealthQueries


def build_health_module(infra: InfrastructureBundle) -> HealthModuleBundle:
    return HealthModuleBundle(
        health_queries=HealthQueries(system_status=infra.system_status),
    )
