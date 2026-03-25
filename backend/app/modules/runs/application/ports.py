from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.runs.domain.models import RunRecord, RuntimeExecutionResult, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind


class RunRepository(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...

    def list(self) -> list[RunRecord]: ...

    def save(self, run: RunRecord) -> None: ...


class TrajectoryRepository(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...

    def append(self, step: TrajectoryStep) -> None: ...


class RunnerPort(Protocol):
    def execute(
        self,
        agent_type: AdapterKind,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult: ...


class RunnerRegistryPort(Protocol):
    def get_runner(self, agent_type: AdapterKind) -> RunnerPort: ...
