from __future__ import annotations

from typing import Protocol

from app.db.persistence import StatePersistence, build_state_persistence, to_uuid


class _SupportsStatePersistence(Protocol):
    @property
    def current(self) -> StatePersistence: ...


class StateStorage:
    def __init__(self) -> None:
        self._persistence = build_state_persistence()

    @property
    def current(self) -> StatePersistence:
        return self._persistence

    @property
    def enabled(self) -> bool:
        return self._persistence.enabled

    def reset_all(self) -> None:
        self._persistence.reset_all()

    def rebuild(self) -> StatePersistence:
        self._persistence.close()
        self._persistence = build_state_persistence()
        return self._persistence


state_storage = StateStorage()


def resolve_state_persistence(
    persistence: StatePersistence | _SupportsStatePersistence | None = None,
) -> StatePersistence:
    if persistence is None:
        return state_storage.current
    if isinstance(persistence, StatePersistence):
        return persistence
    return persistence.current


__all__ = ["resolve_state_persistence", "state_storage", "to_uuid"]
