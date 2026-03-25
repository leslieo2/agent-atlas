from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

TaskFn = Callable[[], None]


class SchedulerPort(Protocol):
    def submit(self, run_id: UUID, fn: TaskFn) -> None: ...


__all__ = ["SchedulerPort", "TaskFn"]
