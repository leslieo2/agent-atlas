from __future__ import annotations

from app.infrastructure.repositories.common import (
    StatePersistenceSource,
    resolve_state_persistence,
    state_storage,
)


class StateSystemStatus:
    def __init__(self, persistence: StatePersistenceSource = None) -> None:
        self._persistence_source = persistence

    def state_initialized(self) -> bool:
        return True

    def persistence_enabled(self) -> bool:
        return bool(resolve_state_persistence(self._persistence_source).enabled)


def reset_state() -> None:
    persistence = state_storage.rebuild()
    persistence.reset_all()


__all__ = ["StateSystemStatus", "reset_state"]
