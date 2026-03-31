from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from agent_atlas_contracts.execution import (
    ExecutionArtifact,
    RunnerRunSpec,
)

from app.execution.contracts import (
    CancelRequest,
    ExecutionCapability,
    ExecutionRunSpec,
    RunHandle,
    RunStatusSnapshot,
)
from app.modules.shared.domain.enums import RunStatus

if TYPE_CHECKING:
    from app.execution.application.results import (
        ProjectedExecutionRecord,
        PublishedRunExecutionResult,
        RunFailureDetails,
        RunnerExecutionResult,
        RunnerSubmissionRecord,
    )


@dataclass(frozen=True)
class ExecutionAttempt:
    attempt: int
    attempt_id: UUID | None


class ExecutionControlPort(Protocol):
    def submit_run(self, run_spec: ExecutionRunSpec) -> RunHandle: ...

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

    def record_runner_submission(
        self,
        run_id: UUID,
        record: RunnerSubmissionRecord,
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


class PublishedRunRuntimePort(Protocol):
    def execute_published(
        self,
        run_id: UUID,
        payload: RunnerRunSpec,
    ) -> PublishedRunExecutionResult: ...


class ArtifactResolverPort(Protocol):
    def resolve(self, payload: ExecutionRunSpec) -> ExecutionArtifact: ...


class RunnerPort(Protocol):
    def execute(self, payload: RunnerRunSpec) -> RunnerExecutionResult: ...
