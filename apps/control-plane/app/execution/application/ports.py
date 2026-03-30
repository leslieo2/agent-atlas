from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from agent_atlas_contracts.execution import ExecutionHandoff

from app.execution.domain.models import (
    CancelRequest,
    ExecutionCapability,
    RunHandle,
    RunStatusSnapshot,
)
from app.modules.runs.application.results import RunnerExecutionResult
from app.modules.runs.domain.models import RunSpec
from app.modules.shared.domain.enums import RunStatus

if TYPE_CHECKING:
    from app.execution.application.service import ProjectedExecutionRecord, RunFailureDetails


@dataclass(frozen=True)
class ExecutionAttempt:
    attempt: int
    attempt_id: UUID | None


class ExecutionControlPort(Protocol):
    def submit_run(self, run_spec: RunSpec) -> RunHandle: ...

    def cancel_run(self, request: CancelRequest) -> bool: ...

    def retry_run(self, run_id: str | UUID) -> RunHandle | None: ...

    def get_status(self, run_id: str | UUID) -> RunStatusSnapshot | None: ...

    def capabilities(self) -> list[ExecutionCapability]: ...


class ExecutionOutcomeSinkPort(Protocol):
    def load_attempt(self, run_id: UUID) -> ExecutionAttempt: ...

    def transition_status(
        self,
        run_id: UUID,
        status: RunStatus,
        reason: str | None = None,
    ) -> bool: ...

    def mark_cancelled_if_requested(self, run_id: UUID) -> bool: ...

    def record_execution_handoff(
        self,
        run_id: UUID,
        handoff: ExecutionHandoff,
    ) -> None: ...

    def record_runner_result(
        self,
        run_id: UUID,
        result: RunnerExecutionResult,
    ) -> None: ...

    def record_projected_execution(
        self,
        run_id: UUID,
        record: ProjectedExecutionRecord,
    ) -> None: ...

    def record_failure(
        self,
        run_id: UUID,
        failure: RunFailureDetails,
    ) -> None: ...
