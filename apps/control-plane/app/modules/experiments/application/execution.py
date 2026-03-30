from __future__ import annotations

from uuid import UUID

from app.execution.application.ports import ExecutionControlPort
from app.modules.agents.application.ports import RunnableAgentCatalogPort
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.experiments.application.ports import (
    ExperimentRepository,
    RunEvaluationRepository,
    RunRepository,
    TrajectoryRepository,
)
from app.modules.experiments.domain.models import ExperimentStatus
from app.modules.experiments.domain.policies import ExperimentAggregate
from app.modules.experiments.domain.scoring import evaluate_run
from app.modules.runs.domain.models import RunSpec
from app.modules.runs.domain.policies import RunAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import RunStatus
from app.modules.shared.domain.models import ApprovalPolicySnapshot, ProvenanceMetadata
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class ExperimentOrchestrator:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        dataset_repository: DatasetRepository,
        run_repository: RunRepository,
        agent_catalog: RunnableAgentCatalogPort,
        execution_control: ExecutionControlPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.dataset_repository = dataset_repository
        self.run_repository = run_repository
        self.agent_catalog = agent_catalog
        self.execution_control = execution_control
        self.task_queue = task_queue

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
        agent = self.agent_catalog.get_agent(experiment.published_agent_id)
        if agent is None:
            failed = ExperimentAggregate.load(experiment).mark_failed(
                error_code="runner_bootstrap",
                error_message=f"agent '{experiment.published_agent_id}' was not found",
            )
            self.experiment_repository.save(failed)
            return

        running = ExperimentAggregate.load(experiment).mark_running()
        self.experiment_repository.save(running)

        model_settings = experiment.spec.model_settings
        prompt_config = experiment.spec.prompt_config
        executor_config = experiment.spec.executor_config
        approval_policy = experiment.spec.approval_policy or ApprovalPolicySnapshot(
            approval_policy_id=experiment.spec.approval_policy_id
        )

        for sample in dataset_version.rows:
            run_spec = RunSpec(
                experiment_id=experiment.experiment_id,
                dataset_version_id=dataset_version.dataset_version_id,
                project=experiment.name,
                dataset=dataset_version.dataset_name,
                agent_id=experiment.published_agent_id,
                model=model_settings.model,
                entrypoint=agent.entrypoint,
                agent_type=agent.adapter_kind(),
                input_summary=sample.input,
                prompt=sample.input,
                tags=list(dict.fromkeys([*experiment.tags, *sample.tags])),
                project_metadata={
                    "prompt_version": prompt_config.prompt_version or "v1",
                    "system_prompt": prompt_config.system_prompt,
                },
                dataset_sample_id=sample.sample_id,
                model_config=model_settings.model_copy(deep=True),
                prompt_config=prompt_config.model_copy(deep=True),
                toolset_config=experiment.spec.toolset_config.model_copy(deep=True),
                evaluator_config=experiment.spec.evaluator_config.model_copy(deep=True),
                executor_config=executor_config.model_copy(deep=True),
                approval_policy=approval_policy.model_copy(deep=True),
                provenance=ProvenanceMetadata(
                    framework=agent.framework,
                    framework_type=agent.framework,
                    framework_version=agent.framework_version,
                    published_agent_snapshot=agent.to_snapshot(),
                    artifact_ref=agent.effective_runtime_artifact().artifact_ref,
                    image_ref=agent.effective_runtime_artifact().image_ref,
                    runner_backend="local-process",
                    executor_backend=executor_config.backend,
                    trace_backend=executor_config.tracing_backend,
                    experiment_id=experiment.experiment_id,
                    dataset_version_id=dataset_version.dataset_version_id,
                    dataset_sample_id=sample.sample_id,
                    approval_policy=approval_policy.model_copy(deep=True),
                    toolset=experiment.spec.toolset_config.model_copy(deep=True),
                    evaluator=experiment.spec.evaluator_config.model_copy(deep=True),
                    executor=executor_config.model_copy(deep=True),
                ),
            )
            run = RunAggregate.create(run_spec)
            self.run_repository.save(run)
            handle = self.execution_control.submit_run(run_spec)
            updated = run.model_copy(
                update={
                    "attempt_id": handle.attempt_id,
                    "executor_backend": handle.backend,
                    "executor_submission_id": handle.executor_ref,
                }
            )
            self.run_repository.save(updated)

        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EXPERIMENT_AGGREGATION,
                target_id=experiment.experiment_id,
                payload={"experiment_id": str(experiment.experiment_id)},
            )
        )


class ExperimentAggregationService:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        run_evaluation_repository: RunEvaluationRepository,
        dataset_repository: DatasetRepository,
        run_repository: RunRepository,
        trajectory_repository: TrajectoryRepository,
        task_queue: TaskQueuePort,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        self.dataset_repository = dataset_repository
        self.run_repository = run_repository
        self.trajectory_repository = trajectory_repository
        self.task_queue = task_queue

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
        runs = [
            run
            for run in self.run_repository.list()
            if run.experiment_id == experiment.experiment_id and run.dataset_sample_id is not None
        ]
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
            self.task_queue.enqueue(
                QueuedTask(
                    task_type=TaskType.EXPERIMENT_AGGREGATION,
                    target_id=experiment.experiment_id,
                    payload={"experiment_id": str(experiment.experiment_id)},
                )
            )
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
                trajectory=self.trajectory_repository.list_for_run(run.run_id),
                scoring_mode=experiment.spec.evaluator_config.scoring_mode,
            )
            self.run_evaluation_repository.save(result)
            results.append(result)
        completed = ExperimentAggregate.load(experiment).complete(results)
        self.experiment_repository.save(completed)
