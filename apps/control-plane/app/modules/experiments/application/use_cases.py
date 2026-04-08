from __future__ import annotations

import builtins

from app.core.errors import AgentNotPublishedError, AppError, DatasetNotFoundError
from app.execution.application.ports import ExecutionControlPort
from app.execution.domain import CancelRequest
from app.modules.agents.application.ports import PublishedAgentCatalogPort
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.experiments.application.ports import (
    ExperimentPolicyResolverPort,
    ExperimentRepository,
    ExperimentRunLookupPort,
    ExperimentRunQueryPort,
    RunEvaluationRepository,
)
from app.modules.experiments.domain.compare import build_compare_result
from app.modules.experiments.domain.models import (
    ExperimentCompareResult,
    ExperimentCreateInput,
    ExperimentRecord,
    ExperimentRunDetail,
    RunEvaluationPatchInput,
    RunEvaluationRecord,
)
from app.modules.experiments.domain.policies import ExperimentAggregate
from app.modules.shared.application.ports import ExecutionJobPort
from app.modules.shared.domain.enums import RunStatus


class ExperimentNotFoundError(AppError, ValueError):
    code = "experiment_not_found"
    status_code = 404

    def __init__(self, experiment_id: str) -> None:
        super().__init__("experiment was not found", experiment_id=experiment_id)


class RunEvaluationNotFoundError(AppError, ValueError):
    code = "run_evaluation_not_found"
    status_code = 404

    def __init__(self, run_id: str) -> None:
        super().__init__("run evaluation was not found", run_id=run_id)


class ExperimentQueries:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        run_query: ExperimentRunQueryPort,
        run_evaluation_repository: RunEvaluationRepository,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_query = run_query
        self.run_evaluation_repository = run_evaluation_repository

    def list(self) -> list[ExperimentRecord]:
        return sorted(
            self.experiment_repository.list(), key=lambda item: item.created_at, reverse=True
        )

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        return self.experiment_repository.get(experiment_id)

    def list_runs(self, experiment_id: str) -> builtins.list[ExperimentRunDetail]:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        return self.run_query.list_details(experiment)

    def compare(
        self, baseline_experiment_id: str, candidate_experiment_id: str
    ) -> ExperimentCompareResult:
        baseline = self.experiment_repository.get(baseline_experiment_id)
        candidate = self.experiment_repository.get(candidate_experiment_id)
        if baseline is None:
            raise ExperimentNotFoundError(baseline_experiment_id)
        if candidate is None:
            raise ExperimentNotFoundError(candidate_experiment_id)
        if baseline.dataset_version_id != candidate.dataset_version_id:
            raise AppError(
                "baseline and candidate experiments must belong to the same dataset version",
                baseline_experiment_id=baseline_experiment_id,
                candidate_experiment_id=candidate_experiment_id,
            )
        baseline_results = {
            record.dataset_sample_id: record
            for record in self.run_evaluation_repository.list_for_experiment(baseline_experiment_id)
        }
        candidate_results = {
            record.dataset_sample_id: record
            for record in self.run_evaluation_repository.list_for_experiment(
                candidate_experiment_id
            )
        }
        return build_compare_result(
            baseline_experiment_id=baseline.experiment_id,
            candidate_experiment_id=candidate.experiment_id,
            dataset_version_id=candidate.dataset_version_id,
            baseline_results=baseline_results,
            candidate_results=candidate_results,
        )


class ExperimentCommands:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        run_evaluation_repository: RunEvaluationRepository,
        dataset_repository: DatasetRepository,
        run_lookup: ExperimentRunLookupPort,
        approval_policy_resolver: ExperimentPolicyResolverPort,
        execution_control: ExecutionControlPort,
        job_queue: ExecutionJobPort,
        agent_catalog: PublishedAgentCatalogPort,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        self.dataset_repository = dataset_repository
        self.run_lookup = run_lookup
        self.approval_policy_resolver = approval_policy_resolver
        self.execution_control = execution_control
        self.job_queue = job_queue
        self.agent_catalog = agent_catalog

    def create(self, payload: ExperimentCreateInput) -> ExperimentRecord:
        dataset_version = self.dataset_repository.get_version(payload.spec.dataset_version_id)
        if dataset_version is None:
            raise DatasetNotFoundError(str(payload.spec.dataset_version_id))
        agent = self.agent_catalog.get_agent(payload.spec.published_agent_id)
        if agent is None:
            raise AgentNotPublishedError(payload.spec.published_agent_id)
        if payload.spec.approval_policy_id is not None:
            policy = self.approval_policy_resolver.resolve(payload.spec.approval_policy_id)
            if policy is None:
                raise AppError(
                    "approval policy was not found",
                    approval_policy_id=str(payload.spec.approval_policy_id),
                )
            payload = payload.model_copy(
                update={
                    "spec": payload.spec.model_copy(
                        update={"approval_policy": policy.model_copy(deep=True)}
                    )
                }
            )
        experiment = ExperimentAggregate.create(
            payload,
            dataset_name=dataset_version.dataset_name,
            sample_count=len(dataset_version.rows),
            published_agent_snapshot=agent.to_snapshot(),
            published_agent_execution_binding=(
                agent.execution_binding.model_copy(deep=True)
                if agent.execution_binding is not None
                else (
                    agent.default_runtime_profile.execution_binding.model_copy(deep=True)
                    if agent.default_runtime_profile.execution_binding is not None
                    else None
                )
            ),
        )
        self.experiment_repository.save(experiment)
        return experiment

    def start(self, experiment_id: str) -> ExperimentRecord:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        experiment = ExperimentAggregate.load(experiment).queue()
        self.experiment_repository.save(experiment)
        self.job_queue.enqueue_experiment_execution(experiment.experiment_id)
        return experiment

    def cancel(self, experiment_id: str) -> ExperimentRecord:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        experiment = ExperimentAggregate.load(experiment).mark_cancelled()
        self.experiment_repository.save(experiment)
        for run in self.run_lookup.list_for_experiment(experiment.experiment_id):
            if run.status not in {
                RunStatus.QUEUED,
                RunStatus.STARTING,
                RunStatus.RUNNING,
                RunStatus.CANCELLING,
            }:
                continue
            self.execution_control.cancel_run(
                CancelRequest(
                    run_id=run.run_id,
                    attempt_id=run.attempt_id,
                    reason="cancelled by experiment",
                )
            )
        return experiment

    def patch_run_evaluation(
        self,
        experiment_id: str,
        run_id: str,
        payload: RunEvaluationPatchInput,
    ) -> RunEvaluationRecord:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        record = self.run_evaluation_repository.get_by_run(run_id)
        if record is None or record.experiment_id != experiment.experiment_id:
            raise RunEvaluationNotFoundError(run_id)
        updated = record.model_copy(
            update={
                "curation_status": payload.curation_status or record.curation_status,
                "curation_note": payload.curation_note
                if payload.curation_note is not None
                else record.curation_note,
                "export_eligible": payload.export_eligible
                if payload.export_eligible is not None
                else record.export_eligible,
            }
        )
        self.run_evaluation_repository.save(updated)
        return updated
