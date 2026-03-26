from __future__ import annotations

from app.db.persistence import build_state_persistence, to_uuid

persistence = build_state_persistence()

__all__ = ["persistence", "to_uuid"]
