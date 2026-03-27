from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.core.errors import AgentNotPublishedError
from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.evals.application.ports import EvalRunGatewayPort
from app.modules.evals.domain.models import EvalDatasetSample, EvalJobRecord, EvalRunState
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput, RunRecord, TrajectoryStep


class _RunReader(Protocol):
    def list(self) -> Sequence[RunRecord]: ...


class _TrajectoryReader(Protocol):
    def list_for_run(self, run_id: str | UUID) -> Sequence[TrajectoryStep]: ...


def _merge_tags(primary: list[str], secondary: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in [*primary, *secondary]:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


class StateEvalRunGateway(EvalRunGatewayPort):
    def __init__(
        self,
        run_repository: _RunReader,
        trajectory_repository: _TrajectoryReader,
        agent_catalog: RunnableAgentCatalogPort,
        run_submission: RunSubmissionService,
    ) -> None:
        self.run_repository = run_repository
        self.trajectory_repository = trajectory_repository
        self.agent_catalog = agent_catalog
        self.run_submission = run_submission

    def create_eval_run(self, job: EvalJobRecord, sample: EvalDatasetSample) -> UUID:
        agent = self.agent_catalog.get_agent(job.agent_id)
        if agent is None:
            raise AgentNotPublishedError(job.agent_id)

        run = self.run_submission.submit(
            RunCreateInput(
                project=job.project,
                dataset=job.dataset,
                eval_job_id=job.eval_job_id,
                dataset_sample_id=sample.sample_id,
                agent_id=job.agent_id,
                input_summary=sample.input,
                prompt=sample.input,
                tags=_merge_tags(job.tags, sample.tags),
                project_metadata={},
            ),
            agent,
        )
        return run.run_id

    def list_eval_runs(self, eval_job_id: str | UUID) -> list[EvalRunState]:
        resolved_eval_job_id = UUID(str(eval_job_id))
        runs = [
            run
            for run in self.run_repository.list()
            if run.eval_job_id == resolved_eval_job_id and run.dataset_sample_id is not None
        ]
        runs.sort(key=lambda run: run.created_at)

        states: list[EvalRunState] = []
        for run in runs:
            trajectory = self.trajectory_repository.list_for_run(run.run_id)
            actual = trajectory[-1].output if trajectory else None
            states.append(
                EvalRunState(
                    run_id=run.run_id,
                    dataset_sample_id=run.dataset_sample_id or "",
                    status=run.status,
                    actual=actual,
                    error_code=run.error_code,
                    error_message=run.error_message,
                    termination_reason=run.termination_reason,
                )
            )
        return states
