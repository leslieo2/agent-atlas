from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.replays.domain.models import ReplayResult
from app.modules.runs.domain.models import TrajectoryStep


class ReplayBaselineReader(Protocol):
    def list_for_run(self, run_id: str | UUID) -> list[TrajectoryStep]: ...


class ReplayRepository(Protocol):
    def get(self, replay_id: str | UUID) -> ReplayResult | None: ...

    def save(self, replay: ReplayResult) -> None: ...
