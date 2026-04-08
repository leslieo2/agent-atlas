from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError

from app.modules.agents.application.ports import PublishedAgentCatalogPort
from app.modules.agents.domain.models import (
    GovernedPublishedAgent,
    normalize_contract_published_agent_snapshot,
)
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.experiments.application.ports import (
    ExperimentAggregationLookupPort,
    ExperimentRepository,
    ExperimentRunLauncherPort,
    ExperimentSampleExecution,
    ExperimentTrajectoryLookupPort,
    RunEvaluationRepository,
)
from app.modules.experiments.domain.models import ExperimentRecord, ExperimentStatus
from app.modules.experiments.domain.policies import ExperimentAggregate
from app.modules.experiments.domain.scoring import evaluate_run
from app.modules.shared.application.ports import ExecutionJobPort
from app.modules.shared.domain.enums import RunStatus


class ExperimentExecutionService:
    def __init__(
        self,
        *,
        experiment_repository: ExperimentRepository,
        dataset_repository: DatasetRepository,
        agent_catalog: PublishedAgentCatalogPort,
        run_launcher: ExperimentRunLauncherPort,
        job_queue: ExecutionJobPort,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.dataset_repository = dataset_repository
        self.agent_catalog = agent_catalog
        self.run_launcher = run_launcher
        self.job_queue = job_queue

    def execute_experiment(self, experiment_id: UUID) -> None:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            return
        dataset_version = self.dataset_repository.get_version(experiment.dataset_version_id)
        if dataset_version is None:
            failed = ExperimentAggregate.load(experiment).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"dataset version '{experiment.dataset_version_id}' was not found",
            )
            self.experiment_repository.save(failed)
            return
        agent = self._resolve_agent(experiment)
        if agent is None:
            failed = ExperimentAggregate.load(experiment).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"agent '{experiment.published_agent_id}' was not found",
            )
            self.experiment_repository.save(failed)
            return

        running = ExperimentAggregate.load(experiment).mark_running()
        self.experiment_repository.save(running)

        for sample in dataset_version.rows:
            self.run_launcher.launch(
                experiment,
                ExperimentSampleExecution(
                    dataset_version_id=dataset_version.dataset_version_id,
                    dataset_name=dataset_version.dataset_name,
                    dataset_sample_id=sample.sample_id,
                    input=sample.input,
                    expected=sample.expected,
                    tags=list(sample.tags),
                    slice=sample.slice,
                    source=sample.source,
                    metadata=sample.metadata,
                    export_eligible=sample.export_eligible,
                ),
                agent,
            )

        self.job_queue.enqueue_experiment_aggregation(experiment.experiment_id)

    def _resolve_agent(self, experiment: ExperimentRecord) -> GovernedPublishedAgent | None:
        if experiment.published_agent_snapshot is not None:
            try:
                snapshot = normalize_contract_published_agent_snapshot(
                    experiment.published_agent_snapshot
                )
                agent = GovernedPublishedAgent.from_snapshot(snapshot)
                if (
                    experiment.published_agent_execution_binding is not None
                    and agent.execution_binding is None
                ):
                    return agent.model_copy(
                        update={
                            "execution_binding": (
                                experiment.published_agent_execution_binding.model_copy(deep=True)
                            )
                        }
                    )
                return agent
            except ValidationError:
                return None
        return self.agent_catalog.get_agent(experiment.published_agent_id)


class ExperimentAggregationService:
    def __init__(
        self,
        *,
        experiment_repository: ExperimentRepository,
        run_evaluation_repository: RunEvaluationRepository,
        dataset_repository: DatasetRepository,
        run_lookup: ExperimentAggregationLookupPort,
        trajectory_lookup: ExperimentTrajectoryLookupPort,
        job_queue: ExecutionJobPort,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        self.dataset_repository = dataset_repository
        self.run_lookup = run_lookup
        self.trajectory_lookup = trajectory_lookup
        self.job_queue = job_queue

    def refresh_experiment(self, experiment_id: UUID) -> None:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            return
        if experiment.status == ExperimentStatus.CANCELLED:
            return
        dataset_version = self.dataset_repository.get_version(experiment.dataset_version_id)
        if dataset_version is None:
            failed = ExperimentAggregate.load(experiment).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"dataset version '{experiment.dataset_version_id}' was not found",
            )
            self.experiment_repository.save(failed)
            return
        runs = self.run_lookup.list_runs(experiment.experiment_id)
        if len(runs) < len(dataset_version.rows) or any(
            run.status
            in {
                RunStatus.QUEUED,
                RunStatus.STARTING,
                RunStatus.RUNNING,
                RunStatus.CANCELLING,
            }
            for run in runs
        ):
            self.job_queue.enqueue_experiment_aggregation(experiment.experiment_id)
            return

        self.run_evaluation_repository.delete_for_experiment(experiment_id)
        runs_by_sample = {run.dataset_sample_id: run for run in runs}
        results = []
        for sample in dataset_version.rows:
            run = runs_by_sample.get(sample.sample_id)
            if run is None:
                continue
            result = evaluate_run(
                experiment_id=experiment.experiment_id,
                dataset_version_id=dataset_version.dataset_version_id,
                sample=sample,
                run=run,
                trajectory=self.trajectory_lookup.list_for_run(run.run_id),
                scoring_mode=experiment.spec.evaluator_config.scoring_mode,
            )
            self.run_evaluation_repository.save(result)
            results.append(result)
        completed = ExperimentAggregate.load(experiment).complete(results)
        self.experiment_repository.save(completed)


__all__ = ["ExperimentAggregationService", "ExperimentExecutionService"]
