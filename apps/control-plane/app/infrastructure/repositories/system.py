from __future__ import annotations

from app.infrastructure.repositories.common import persistence


class StateSystemStatus:
    def state_initialized(self) -> bool:
        return True

    def persistence_enabled(self) -> bool:
        return bool(persistence.enabled)


def reset_state() -> None:
    persistence.rebuild()
    persistence.reset_all()


__all__ = ["StateSystemStatus", "reset_state"]
