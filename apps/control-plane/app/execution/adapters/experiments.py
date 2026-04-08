from __future__ import annotations

from uuid import UUID

from app.modules.agents.domain.models import GovernedPublishedAgent
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.experiments.application.ports import (
    ExperimentAggregationLookupPort,
    ExperimentAggregationRun,
    ExperimentRunLauncherPort,
    ExperimentRunLookupPort,
    ExperimentRunQueryPort,
    ExperimentRunRef,
    ExperimentSampleExecution,
    ExperimentTrajectoryLookupPort,
    RunEvaluationRepository,
)
from app.modules.experiments.domain.models import ExperimentRecord, ExperimentRunDetail
from app.modules.runs.application.ports import RunRepository, TrajectoryRepository
from app.modules.runs.application.services import RunSubmissionService
from app.modules.runs.domain.models import RunCreateInput
from app.modules.shared.domain.enums import CurationStatus
from app.modules.shared.domain.policies import ApprovalPolicySnapshot


class RunSubmissionExperimentLauncher(ExperimentRunLauncherPort):
    def __init__(self, run_submission: RunSubmissionService) -> None:
        self.run_submission = run_submission

    def launch(
        self,
        experiment: ExperimentRecord,
        sample: ExperimentSampleExecution,
        agent: GovernedPublishedAgent,
    ) -> None:
        approval_policy = experiment.spec.approval_policy or ApprovalPolicySnapshot(
            approval_policy_id=experiment.spec.approval_policy_id
        )
        run_input = RunCreateInput(
            experiment_id=experiment.experiment_id,
            dataset_version_id=sample.dataset_version_id,
            project=experiment.name,
            dataset=sample.dataset_name,
            agent_id=experiment.published_agent_id,
            input_summary=sample.input,
            prompt=sample.input,
            tags=list(dict.fromkeys([*experiment.tags, *sample.tags])),
            project_metadata={
                "prompt_version": experiment.spec.prompt_config.prompt_version or "v1",
                "system_prompt": experiment.spec.prompt_config.system_prompt,
            },
            execution_target=(
                experiment.spec.execution_target.model_copy(deep=True)
                if experiment.spec.execution_target is not None
                else None
            ),
            dataset_sample_id=sample.dataset_sample_id,
            model_settings=experiment.spec.model_settings.model_copy(deep=True),
            prompt_config=experiment.spec.prompt_config.model_copy(deep=True),
            toolset_config=experiment.spec.toolset_config.model_copy(deep=True),
            evaluator_config=experiment.spec.evaluator_config.model_copy(deep=True),
            approval_policy=approval_policy.model_copy(deep=True),
        )
        if experiment.spec.executor_config is not None:
            run_input = run_input.model_copy(
                update={
                    "executor_config": experiment.spec.executor_config.model_copy(deep=True),
                    "execution_binding": (
                        experiment.spec.execution_binding.model_copy(deep=True)
                        if experiment.spec.execution_binding is not None
                        else None
                    ),
                }
            )
        self.run_submission.submit(run_input, agent)


class RunBackedExperimentRunLookup(
    ExperimentRunLookupPort,
    ExperimentAggregationLookupPort,
):
    def __init__(self, run_repository: RunRepository) -> None:
        self.run_repository = run_repository

    def list_for_experiment(self, experiment_id: str | UUID) -> list[ExperimentRunRef]:
        runs = self._list_runs(experiment_id)
        return [
            ExperimentRunRef(
                run_id=run.run_id,
                attempt_id=run.attempt_id,
                dataset_sample_id=run.dataset_sample_id,
                status=run.status,
            )
            for run in runs
        ]

    def list_runs(self, experiment_id: str | UUID) -> list[ExperimentAggregationRun]:
        runs = self._list_runs(experiment_id)
        return [
            ExperimentAggregationRun(
                run_id=run.run_id,
                dataset_sample_id=run.dataset_sample_id,
                status=run.status,
                created_at=run.created_at,
                error_message=run.error_message,
                termination_reason=run.termination_reason,
                error_code=run.error_code,
                trace_pointer=run.trace_pointer.model_copy(deep=True)
                if run.trace_pointer is not None
                else None,
                provenance=run.provenance.model_copy(deep=True)
                if run.provenance is not None
                else None,
                artifact_ref=run.artifact_ref,
                image_ref=run.image_ref,
                executor_backend=run.executor_backend,
                latency_ms=run.latency_ms,
                tool_calls=run.tool_calls,
                container_image=run.container_image,
            )
            for run in runs
        ]

    def _list_runs(self, experiment_id: str | UUID):
        experiment_uuid = UUID(str(experiment_id))
        runs = [
            run
            for run in self.run_repository.list()
            if run.experiment_id == experiment_uuid and run.dataset_sample_id is not None
        ]
        runs.sort(key=lambda run: run.created_at)
        return runs


class RunBackedExperimentRunQuery(ExperimentRunQueryPort):
    def __init__(
        self,
        *,
        dataset_repository: DatasetRepository,
        run_repository: RunRepository,
        run_evaluation_repository: RunEvaluationRepository,
    ) -> None:
        self.dataset_repository = dataset_repository
        self.run_repository = run_repository
        self.run_evaluation_repository = run_evaluation_repository

    def list_details(self, experiment: ExperimentRecord) -> list[ExperimentRunDetail]:
        dataset_version = self.dataset_repository.get_version(experiment.dataset_version_id)
        samples_by_id = {
            sample.sample_id: sample
            for sample in (dataset_version.rows if dataset_version is not None else [])
        }
        evaluations_by_run = {
            record.run_id: record
            for record in self.run_evaluation_repository.list_for_experiment(
                experiment.experiment_id
            )
        }
        runs = [
            run
            for run in self.run_repository.list()
            if run.experiment_id == experiment.experiment_id and run.dataset_sample_id is not None
        ]
        runs.sort(key=lambda run: run.created_at)

        details: list[ExperimentRunDetail] = []
        for run in runs:
            sample = samples_by_id.get(run.dataset_sample_id or "")
            evaluation = evaluations_by_run.get(run.run_id)
            details.append(
                ExperimentRunDetail(
                    run_id=run.run_id,
                    experiment_id=experiment.experiment_id,
                    dataset_sample_id=run.dataset_sample_id or "",
                    input=evaluation.input
                    if evaluation
                    else (sample.input if sample else run.input_summary),
                    expected=evaluation.expected
                    if evaluation
                    else (sample.expected if sample else None),
                    actual=evaluation.actual if evaluation else None,
                    run_status=run.status,
                    judgement=evaluation.judgement if evaluation else None,
                    failure_reason=evaluation.failure_reason if evaluation else None,
                    error_code=evaluation.error_code if evaluation else run.error_code,
                    error_message=evaluation.error_message if evaluation else run.error_message,
                    tags=list(evaluation.tags)
                    if evaluation
                    else (list(sample.tags) if sample else list(run.tags)),
                    slice=evaluation.slice if evaluation else (sample.slice if sample else None),
                    source=evaluation.source if evaluation else (sample.source if sample else None),
                    export_eligible=evaluation.export_eligible
                    if evaluation
                    else (sample.export_eligible if sample else None),
                    curation_status=evaluation.curation_status
                    if evaluation
                    else CurationStatus.REVIEW,
                    curation_note=evaluation.curation_note if evaluation else None,
                    published_agent_snapshot=evaluation.published_agent_snapshot
                    if evaluation
                    else (run.provenance.published_agent_snapshot if run.provenance else None),
                    artifact_ref=evaluation.artifact_ref if evaluation else run.artifact_ref,
                    image_ref=evaluation.image_ref if evaluation else run.image_ref,
                    executor_backend=evaluation.executor_backend
                    if evaluation
                    else run.executor_backend,
                    latency_ms=evaluation.latency_ms if evaluation else run.latency_ms,
                    tool_calls=evaluation.tool_calls if evaluation else run.tool_calls,
                    trace_url=_resolve_trace_url(evaluation=evaluation, run=run),
                )
            )
        return details


class TrajectoryRepositoryExperimentLookup(ExperimentTrajectoryLookupPort):
    def __init__(self, trajectory_repository: TrajectoryRepository) -> None:
        self.trajectory_repository = trajectory_repository

    def list_for_run(self, run_id: str | UUID):
        return self.trajectory_repository.list_for_run(run_id)


def _resolve_trace_url(*, evaluation, run) -> str | None:
    if evaluation and isinstance(evaluation.trace_url, str) and evaluation.trace_url.strip():
        return evaluation.trace_url.strip()
    if (
        run.trace_pointer is not None
        and isinstance(run.trace_pointer.trace_url, str)
        and run.trace_pointer.trace_url.strip()
    ):
        return run.trace_pointer.trace_url.strip()
    if (
        run.trace_pointer is not None
        and isinstance(run.trace_pointer.project_url, str)
        and run.trace_pointer.project_url.strip()
    ):
        return run.trace_pointer.project_url.strip()
    return None


__all__ = [
    "RunBackedExperimentRunLookup",
    "RunBackedExperimentRunQuery",
    "RunSubmissionExperimentLauncher",
    "TrajectoryRepositoryExperimentLookup",
]
