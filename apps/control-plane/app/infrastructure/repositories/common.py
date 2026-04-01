from __future__ import annotations

from typing import Any

from app.db.persistence import StatePersistence, build_state_persistence, to_uuid


class PersistenceProxy:
    def __init__(self) -> None:
        self._persistence = build_state_persistence()

    def rebuild(self) -> StatePersistence:
        self._persistence.close()
        self._persistence = build_state_persistence()
        return self._persistence

    def __getattr__(self, name: str) -> Any:
        return getattr(self._persistence, name)


persistence = PersistenceProxy()

__all__ = ["persistence", "to_uuid"]
