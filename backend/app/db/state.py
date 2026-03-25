from __future__ import annotations

from app.db.persistence import StatePersistence, build_state_persistence, serialize_model, to_uuid
from app.db.store import StateStore

state = StateStore(build_state_persistence())

__all__ = [
    "StatePersistence",
    "StateStore",
    "build_state_persistence",
    "serialize_model",
    "state",
    "to_uuid",
]
