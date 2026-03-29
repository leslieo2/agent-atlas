from __future__ import annotations

from urllib.parse import quote, urlencode

from app.core.errors import AgentNotPublishedError, AppError, DatasetNotFoundError
from app.modules.evals.application.ports import (
    AgentLookupPort,
    DatasetSourcePort,
    EvalJobRepository,
    EvalSampleResultRepository,
)
from app.modules.evals.domain.models import (
    CandidateRunSummary,
    CompareOutcome,
    EvalCompareResult,
    EvalCompareSample,
    EvalJobCreateInput,
    EvalJobRecord,
    EvalSamplePatchInput,
    EvalSampleResult,
    SampleJudgement,
)
from app.modules.evals.domain.policies import EvalJobAggregate
from app.modules.shared.application.ports import TaskQueuePort
from app.modules.shared.domain.models import ObservabilityMetadata
from app.modules.shared.domain.tasks import QueuedTask, TaskType


class EvalCompareMismatchError(AppError, ValueError):
    code = "eval_compare_mismatch"
    status_code = 400


class EvalSampleNotFoundError(AppError, ValueError):
    code = "eval_sample_not_found"
    status_code = 404

    def __init__(self, eval_job_id: str, dataset_sample_id: str) -> None:
        super().__init__(
            "eval sample was not found",
            eval_job_id=eval_job_id,
            dataset_sample_id=dataset_sample_id,
        )


class EvalJobNotFoundError(AppError, ValueError):
    code = "eval_job_not_found"
    status_code = 404

    def __init__(self, eval_job_id: str) -> None:
        super().__init__("eval job was not found", eval_job_id=eval_job_id)


def _compare_outcome(
    baseline: EvalSampleResult | None,
    candidate: EvalSampleResult | None,
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


def _distribution(samples: list[EvalCompareSample]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sample in samples:
        key = sample.compare_outcome.value
        counts[key] = counts.get(key, 0) + 1
    return counts


class EvalJobQueries:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        sample_result_repository: EvalSampleResultRepository,
        phoenix_base_url: str | None = None,
        phoenix_project_id: str | None = None,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.sample_result_repository = sample_result_repository
        self.phoenix_base_url = phoenix_base_url.rstrip("/") if phoenix_base_url else None
        self.phoenix_project_id = phoenix_project_id

    def list_jobs(self) -> list[EvalJobRecord]:
        jobs = sorted(
            self.eval_job_repository.list(),
            key=lambda job: job.created_at,
            reverse=True,
        )
        return [self._with_observability(job) for job in jobs]

    def get_job(self, eval_job_id: str) -> EvalJobRecord | None:
        job = self.eval_job_repository.get(eval_job_id)
        return self._with_observability(job) if job else None

    def list_samples(self, eval_job_id: str) -> list[EvalSampleResult]:
        return self.sample_result_repository.list_for_job(eval_job_id)

    def get_sample(self, eval_job_id: str, dataset_sample_id: str) -> EvalSampleResult | None:
        return self.sample_result_repository.get(eval_job_id, dataset_sample_id)

    def compare_jobs(
        self,
        baseline_eval_job_id: str,
        candidate_eval_job_id: str,
    ) -> EvalCompareResult:
        baseline_job = self.eval_job_repository.get(baseline_eval_job_id)
        candidate_job = self.eval_job_repository.get(candidate_eval_job_id)
        if baseline_job is None:
            raise EvalJobNotFoundError(baseline_eval_job_id)
        if candidate_job is None:
            raise EvalJobNotFoundError(candidate_eval_job_id)
        if baseline_job.dataset != candidate_job.dataset:
            raise EvalCompareMismatchError(
                "baseline and candidate eval jobs must belong to the same dataset",
                baseline_eval_job_id=str(baseline_job.eval_job_id),
                candidate_eval_job_id=str(candidate_job.eval_job_id),
            )

        baseline_results = {
            result.dataset_sample_id: result
            for result in self.sample_result_repository.list_for_job(baseline_job.eval_job_id)
        }
        candidate_results = {
            result.dataset_sample_id: result
            for result in self.sample_result_repository.list_for_job(candidate_job.eval_job_id)
        }

        sample_ids = sorted(set(baseline_results) | set(candidate_results))
        samples: list[EvalCompareSample] = []
        for sample_id in sample_ids:
            baseline = baseline_results.get(sample_id)
            candidate = candidate_results.get(sample_id)
            chosen = candidate or baseline
            outcome = _compare_outcome(baseline, candidate)
            samples.append(
                EvalCompareSample(
                    dataset_sample_id=sample_id,
                    baseline_judgement=baseline.judgement if baseline else None,
                    candidate_judgement=candidate.judgement if candidate else None,
                    compare_outcome=outcome,
                    error_code=(
                        candidate.error_code
                        if candidate and candidate.error_code
                        else baseline.error_code
                        if baseline
                        else None
                    ),
                    slice=chosen.slice if chosen else None,
                    tags=list(chosen.tags) if chosen else [],
                    candidate_run_summary=(
                        CandidateRunSummary(
                            run_id=candidate.run_id,
                            actual=candidate.actual,
                            trace_url=candidate.trace_url,
                        )
                        if candidate
                        else None
                    ),
                )
            )

        return EvalCompareResult(
            baseline_eval_job_id=baseline_job.eval_job_id,
            candidate_eval_job_id=candidate_job.eval_job_id,
            dataset=candidate_job.dataset,
            distribution=_distribution(samples),
            samples=samples,
        )

    def _with_observability(self, job: EvalJobRecord) -> EvalJobRecord:
        if not self.phoenix_base_url:
            return job
        return job.model_copy(
            update={
                "observability": ObservabilityMetadata(
                    backend="phoenix",
                    project_url=self._build_project_url(job.eval_job_id),
                )
            }
        )

    def _build_project_url(self, eval_job_id: object) -> str:
        if not self.phoenix_project_id:
            return self.phoenix_base_url or ""
        path = f"{self.phoenix_base_url}/projects/{quote(self.phoenix_project_id, safe='')}"
        return f"{path}?{urlencode({'eval_job_id': str(eval_job_id)})}"


class EvalJobCommands:
    def __init__(
        self,
        eval_job_repository: EvalJobRepository,
        sample_result_repository: EvalSampleResultRepository,
        dataset_source: DatasetSourcePort,
        agent_lookup: AgentLookupPort,
        task_queue: TaskQueuePort,
    ) -> None:
        self.eval_job_repository = eval_job_repository
        self.sample_result_repository = sample_result_repository
        self.dataset_source = dataset_source
        self.agent_lookup = agent_lookup
        self.task_queue = task_queue

    def create_job(self, payload: EvalJobCreateInput) -> EvalJobRecord:
        dataset = self.dataset_source.get(payload.dataset)
        if dataset is None:
            raise DatasetNotFoundError(payload.dataset)
        if not self.agent_lookup.exists(payload.agent_id):
            raise AgentNotPublishedError(payload.agent_id)

        job = EvalJobAggregate.create(payload, sample_count=len(dataset.samples))
        self.eval_job_repository.save(job)
        self.task_queue.enqueue(
            QueuedTask(
                task_type=TaskType.EVAL_EXECUTION,
                target_id=job.eval_job_id,
                payload={"eval_job_id": str(job.eval_job_id)},
            )
        )
        return job

    def patch_sample(
        self,
        eval_job_id: str,
        dataset_sample_id: str,
        payload: EvalSamplePatchInput,
    ) -> EvalSampleResult:
        result = self.sample_result_repository.get(eval_job_id, dataset_sample_id)
        if result is None:
            raise EvalSampleNotFoundError(eval_job_id, dataset_sample_id)

        updated = result.model_copy(
            update={
                "curation_status": payload.curation_status or result.curation_status,
                "curation_note": (
                    payload.curation_note
                    if payload.curation_note is not None
                    else result.curation_note
                ),
                "export_eligible": (
                    payload.export_eligible
                    if payload.export_eligible is not None
                    else result.export_eligible
                ),
            }
        )
        self.sample_result_repository.save(updated)
        return updated


__all__ = [
    "EvalCompareMismatchError",
    "EvalJobCommands",
    "EvalJobNotFoundError",
    "EvalJobQueries",
    "EvalSampleNotFoundError",
]
