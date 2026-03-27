from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    RUN_EXECUTION = "run_execution"
    EVAL_EXECUTION = "eval_execution"
    EVAL_AGGREGATION = "eval_aggregation"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class QueuedTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    task_type: TaskType
    target_id: UUID
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    error: str | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
