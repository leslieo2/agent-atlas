from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.shared.domain.enums import RunStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class Heartbeat(BaseModel):
    run_id: UUID
    attempt_id: UUID
    backend: str
    sequence: int
    status: RunStatus
    occurred_at: datetime = Field(default_factory=utc_now)
    lease_expires_at: datetime | None = None
    last_progress_at: datetime | None = None
    phase_hint: str | None = None
