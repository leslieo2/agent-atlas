from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.execution.domain.models import (
    CancelRequest,
    ExecutionCapability,
    RunHandle,
    RunStatusSnapshot,
)
from app.modules.runs.domain.models import RunSpec


class ExecutionControlPort(Protocol):
    def submit_run(self, run_spec: RunSpec) -> RunHandle: ...

    def cancel_run(self, request: CancelRequest) -> bool: ...

    def retry_run(self, run_id: str | UUID) -> RunHandle | None: ...

    def get_status(self, run_id: str | UUID) -> RunStatusSnapshot | None: ...

    def capabilities(self) -> list[ExecutionCapability]: ...
