from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.replays.domain.models import ReplayResult
from app.modules.runs.domain.models import RunRecord, RuntimeExecutionResult, TrajectoryStep
from app.modules.shared.domain.enums import AdapterKind


class ReplayBaselineReader(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...


class ReplayRunReader(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...


class ReplayRuntimePort(Protocol):
    def execute(
        self,
        agent_type: AdapterKind,
        model: str,
        prompt: str,
    ) -> RuntimeExecutionResult: ...


class ReplayRuntimeRegistryPort(Protocol):
    def get_runner(self, agent_type: AdapterKind) -> ReplayRuntimePort: ...


class ReplayRepository(Protocol):
    def get(self, replay_id: str | UUID) -> ReplayResult | None: ...

    def save(self, replay: ReplayResult) -> None: ...
