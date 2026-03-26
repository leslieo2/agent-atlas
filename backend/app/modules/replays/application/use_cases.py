from __future__ import annotations

from uuid import UUID

from app.core.errors import UnsupportedOperationError
from app.modules.replays.application.execution import (
    ReplayBaselineResolver,
    ReplayExecutor,
    ReplayResultFactory,
)
from app.modules.replays.application.ports import (
    ReplayBaselineReader,
    ReplayRepository,
    ReplayRunReader,
)
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
        run_repository: ReplayRunReader,
        replay_repository: ReplayRepository,
        baseline_resolver: ReplayBaselineResolver | None = None,
        replay_executor: ReplayExecutor | None = None,
        result_factory: ReplayResultFactory | None = None,
    ) -> None:
        self.trajectory_repository = trajectory_repository
        self.run_repository = run_repository
        self.replay_repository = replay_repository
        self.baseline_resolver = baseline_resolver or ReplayBaselineResolver()
        if replay_executor is None:
            raise ValueError("replay_executor must be configured")
        self.replay_executor = replay_executor
        self.result_factory = result_factory or ReplayResultFactory()

    def replay_step(self, request: ReplayRequest) -> ReplayResult:
        run = self.run_repository.get(request.run_id)
        if not run:
            raise KeyError(f"run '{request.run_id}' not found")
        if run.agent_id:
            raise UnsupportedOperationError(
                "replay is not supported for registered agent runs",
                operation="replay",
                run_id=str(request.run_id),
                agent_id=run.agent_id,
            )
        baseline_step = self.baseline_resolver.resolve(
            self.trajectory_repository.list_for_run(request.run_id),
            request.step_id,
        )
        replay_result, resolved_model = self.replay_executor.execute(request, baseline_step, run)
        result = self.result_factory.build(request, baseline_step, replay_result, resolved_model)
        self.replay_repository.save(result)
        return result
