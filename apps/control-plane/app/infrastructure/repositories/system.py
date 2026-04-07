from __future__ import annotations

from app.db.persistence import StatePersistence
from app.infrastructure.repositories.common import resolve_state_persistence, state_storage


class StateSystemStatus:
    def __init__(self, persistence: StatePersistence | None = None) -> None:
        self._persistence = persistence

    def state_initialized(self) -> bool:
        return True

    def persistence_enabled(self) -> bool:
        return bool(resolve_state_persistence(self._persistence).enabled)


def reset_state() -> None:
    persistence = state_storage.rebuild()
    persistence.reset_all()


__all__ = ["StateSystemStatus", "reset_state"]
