from __future__ import annotations

from uuid import UUID

from app.modules.replays.application.execution import (
    ReplayBaselineResolver,
    ReplayExecutor,
    ReplayResultFactory,
)
from app.modules.replays.application.ports import ReplayBaselineReader, ReplayRepository
from app.modules.replays.domain.models import ReplayRequest, ReplayResult


class ReplayQueries:
    def __init__(self, replay_repository: ReplayRepository) -> None:
        self.replay_repository = replay_repository

    def get_replay(self, replay_id: str | UUID) -> ReplayResult | None:
        return self.replay_repository.get(replay_id)


class ReplayCommands:
    def __init__(
        self,
        trajectory_repository: ReplayBaselineReader,
        replay_repository: ReplayRepository,
        baseline_resolver: ReplayBaselineResolver | None = None,
        replay_executor: ReplayExecutor | None = None,
        result_factory: ReplayResultFactory | None = None,
    ) -> None:
        self.trajectory_repository = trajectory_repository
        self.replay_repository = replay_repository
        self.baseline_resolver = baseline_resolver or ReplayBaselineResolver()
        self.replay_executor = replay_executor or ReplayExecutor()
        self.result_factory = result_factory or ReplayResultFactory()

    def replay_step(self, request: ReplayRequest) -> ReplayResult:
        baseline_step = self.baseline_resolver.resolve(
            self.trajectory_repository.list_for_run(request.run_id),
            request.step_id,
        )
        replay_output = self.replay_executor.execute(request, baseline_step)
        result = self.result_factory.build(request, baseline_step, replay_output)
        self.replay_repository.save(result)
        return result
