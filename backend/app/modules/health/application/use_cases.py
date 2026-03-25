from __future__ import annotations

from app.modules.health.application.ports import SystemStatusPort


class HealthQueries:
    def __init__(self, system_status: SystemStatusPort) -> None:
        self.system_status = system_status

    def get_health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "components": {
                "state_initialized": self.system_status.state_initialized(),
                "state_persistence_enabled": self.system_status.persistence_enabled(),
            },
        }
