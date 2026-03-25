from __future__ import annotations

from uuid import UUID

from app.db.state import state


def to_uuid(value: str | UUID) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)


__all__ = ["state", "to_uuid"]
