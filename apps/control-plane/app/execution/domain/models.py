from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

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


class ExecutionCapability(BaseModel):
    backend: str
    production_ready: bool
    supports_cancel: bool
    supports_retry: bool
    supports_status: bool
    supports_heartbeat: bool


class RunHandle(BaseModel):
    run_id: UUID
    attempt_id: UUID = Field(default_factory=uuid4)
    backend: str
    executor_ref: str
    submitted_at: datetime = Field(default_factory=utc_now)


class CancelRequest(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    reason: str = "cancelled by user"


class RunTerminalSummary(BaseModel):
    run_id: UUID
    attempt_id: UUID
    status: RunStatus
    backend: str
    reason_code: str | None = None
    reason_message: str | None = None
    exit_code: int | None = None
    artifact_ref: str | None = None
    image_ref: str | None = None
    trace_url: str | None = None
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=utc_now)


class RunStatusSnapshot(BaseModel):
    run_id: UUID
    attempt_id: UUID | None = None
    backend: str | None = None
    executor_ref: str | None = None
    status: RunStatus
    reason_code: str | None = None
    reason_message: str | None = None
    heartbeat: Heartbeat | None = None
    terminal_summary: RunTerminalSummary | None = None
