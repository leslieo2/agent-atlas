from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.health.application.use_cases import HealthQueries


def get_health_queries() -> HealthQueries:
    return get_container().health.health_queries
