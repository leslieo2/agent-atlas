from __future__ import annotations

import builtins
from collections import Counter
from collections.abc import Callable
from uuid import UUID

from app.core.errors import AgentNotPublishedError, AppError, DatasetNotFoundError
from app.execution.application.ports import ExecutionControlPort
from app.execution.contracts import CancelRequest
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.experiments.application.ports import (
    ExperimentRepository,
    RunEvaluationRepository,
    RunRepository,
)
from app.modules.experiments.domain.models import (
    CandidateRunSummary,
    ExperimentCompareResult,
    ExperimentCompareSample,
    ExperimentCreateInput,
    ExperimentRecord,
    ExperimentRunDetail,
    RunEvaluationPatchInput,
    RunEvaluationRecord,
)
from app.modules.experiments.domain.policies import ExperimentAggregate
from app.modules.policies.application.ports import ApprovalPolicyRepository
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.enums import (
    CompareOutcome,
    CurationStatus,
    RunStatus,
    SampleJudgement,
)
from app.modules.shared.domain.tasks import QueuedTask, TaskType


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


def _compare_outcome(
    baseline,
    candidate,
) -> CompareOutcome:
    if baseline is None:
        return CompareOutcome.CANDIDATE_ONLY
    if candidate is None:
        return CompareOutcome.BASELINE_ONLY
    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.UNCHANGED_PASS
    if (
        baseline.judgement != SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.IMPROVED
    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement != SampleJudgement.PASSED
    ):
        return CompareOutcome.REGRESSED
    return CompareOutcome.UNCHANGED_FAIL


class ExperimentQueries:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        run_evaluation_repository: RunEvaluationRepository,
        run_repository: RunRepository,
        dataset_repository: DatasetRepository,
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        self.run_repository = run_repository
        self.dataset_repository = dataset_repository

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
        dataset_version = self.dataset_repository.get_version(experiment.dataset_version_id)
        samples_by_id = {
            sample.sample_id: sample
            for sample in (dataset_version.rows if dataset_version is not None else [])
        }
        evaluations_by_run = {
            record.run_id: record
            for record in self.run_evaluation_repository.list_for_experiment(experiment_id)
        }
        runs = [
            run
            for run in self.run_repository.list()
            if run.experiment_id == UUID(str(experiment_id)) and run.dataset_sample_id is not None
        ]
        runs.sort(key=lambda run: run.created_at)
        details: builtins.list[ExperimentRunDetail] = []
        for run in runs:
            sample = samples_by_id.get(run.dataset_sample_id or "")
            evaluation = evaluations_by_run.get(run.run_id)
            details.append(
                ExperimentRunDetail(
                    run_id=run.run_id,
                    experiment_id=UUID(str(experiment_id)),
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
                    trace_url=evaluation.trace_url
                    if evaluation
                    else (run.trace_pointer.trace_url if run.trace_pointer else None),
                )
            )
        return details

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
        sample_ids = sorted(set(baseline_results) | set(candidate_results))
        samples: list[ExperimentCompareSample] = []
        for sample_id in sample_ids:
            baseline_result = baseline_results.get(sample_id)
            candidate_result = candidate_results.get(sample_id)
            chosen = candidate_result or baseline_result
            outcome = _compare_outcome(baseline_result, candidate_result)
            samples.append(
                ExperimentCompareSample(
                    dataset_sample_id=sample_id,
                    baseline_judgement=baseline_result.judgement if baseline_result else None,
                    candidate_judgement=candidate_result.judgement if candidate_result else None,
                    compare_outcome=outcome,
                    error_code=(
                        candidate_result.error_code
                        if candidate_result and candidate_result.error_code
                        else baseline_result.error_code
                        if baseline_result
                        else None
                    ),
                    slice=chosen.slice if chosen else None,
                    tags=list(chosen.tags) if chosen else [],
                    candidate_run_summary=(
                        CandidateRunSummary(
                            run_id=candidate_result.run_id,
                            actual=candidate_result.actual,
                            trace_url=candidate_result.trace_url,
                        )
                        if candidate_result
                        else None
                    ),
                )
            )
        distribution = Counter(sample.compare_outcome.value for sample in samples)
        return ExperimentCompareResult(
            baseline_experiment_id=baseline.experiment_id,
            candidate_experiment_id=candidate.experiment_id,
            dataset_version_id=candidate.dataset_version_id,
            distribution=dict(distribution),
            samples=samples,
        )


class ExperimentCommands:
    def __init__(
        self,
        experiment_repository: ExperimentRepository,
        run_evaluation_repository: RunEvaluationRepository,
        dataset_repository: DatasetRepository,
        run_repository: RunRepository,
        approval_policy_repository: ApprovalPolicyRepository,
        execution_control: ExecutionControlPort,
        task_queue: TaskQueuePort,
        agent_exists: Callable[[str], bool],
    ) -> None:
        self.experiment_repository = experiment_repository
        self.run_evaluation_repository = run_evaluation_repository
        self.dataset_repository = dataset_repository
        self.run_repository = run_repository
        self.approval_policy_repository = approval_policy_repository
        self.execution_control = execution_control
        self.task_queue = task_queue
        self.agent_exists = agent_exists

    def create(self, payload: ExperimentCreateInput) -> ExperimentRecord:
        dataset_version = self.dataset_repository.get_version(payload.spec.dataset_version_id)
        if dataset_version is None:
            raise DatasetNotFoundError(str(payload.spec.dataset_version_id))
        if not self.agent_exists(payload.spec.published_agent_id):
            raise AgentNotPublishedError(payload.spec.published_agent_id)
        if payload.spec.approval_policy_id is not None:
            policy = self.approval_policy_repository.get(payload.spec.approval_policy_id)
            if policy is None:
                raise AppError(
                    "approval policy was not found",
                    approval_policy_id=str(payload.spec.approval_policy_id),
                )
            payload = payload.model_copy(
                update={
                    "spec": payload.spec.model_copy(
                        update={
                            "approval_policy": {
                                "approval_policy_id": policy.approval_policy_id,
                                "name": policy.name,
                                "tool_policies": [
                                    rule.model_copy(deep=True) for rule in policy.tool_policies
                                ],
                            }
                        }
                    )
                }
            )
        experiment = ExperimentAggregate.create(
            payload,
            dataset_name=dataset_version.dataset_name,
            sample_count=len(dataset_version.rows),
        )
        self.experiment_repository.save(experiment)
        return experiment

    def start(self, experiment_id: str) -> ExperimentRecord:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        experiment = ExperimentAggregate.load(experiment).queue()
        self.experiment_repository.save(experiment)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EXPERIMENT_EXECUTION,
                target_id=experiment.experiment_id,
                payload={"experiment_id": str(experiment.experiment_id)},
            )
        )
        return experiment

    def cancel(self, experiment_id: str) -> ExperimentRecord:
        experiment = self.experiment_repository.get(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        experiment = ExperimentAggregate.load(experiment).mark_cancelled()
        self.experiment_repository.save(experiment)
        for run in self.run_repository.list():
            if run.experiment_id != experiment.experiment_id:
                continue
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
