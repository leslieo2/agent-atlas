from __future__ import annotations

from app.modules.evals.domain.models import (
    EvalJobCreateInput,
    EvalJobRecord,
    EvalJobStatus,
    EvalSampleResult,
    SampleJudgement,
)


class EvalJobAggregate:
    def __init__(self, job: EvalJobRecord) -> None:
        self.job = job

    @classmethod
    def create(cls, payload: EvalJobCreateInput, sample_count: int) -> EvalJobRecord:
        return EvalJobRecord(
            agent_id=payload.agent_id,
            dataset=payload.dataset,
            project=payload.project,
            tags=payload.tags,
            scoring_mode=payload.scoring_mode,
            sample_count=sample_count,
        )

    @classmethod
    def load(cls, job: EvalJobRecord) -> EvalJobAggregate:
        return cls(job)

    def mark_running(self) -> EvalJobRecord:
        if self.job.status != EvalJobStatus.QUEUED:
            raise ValueError(f"cannot start eval job from status={self.job.status.value}")
        self.job.status = EvalJobStatus.RUNNING
        self.job.error_code = None
        self.job.error_message = None
        return self.job

    def complete(self, sample_results: list[EvalSampleResult]) -> EvalJobRecord:
        passed_count = sum(
            1 for result in sample_results if result.judgement == SampleJudgement.PASSED
        )
        failed_count = sum(
            1 for result in sample_results if result.judgement == SampleJudgement.FAILED
        )
        unscored_count = sum(
            1 for result in sample_results if result.judgement == SampleJudgement.UNSCORED
        )
        runtime_error_count = sum(
            1 for result in sample_results if result.judgement == SampleJudgement.RUNTIME_ERROR
        )
        scored_count = passed_count + failed_count + runtime_error_count
        denominator = max(1, scored_count)
        failure_distribution: dict[str, int] = {}

        for result in sample_results:
            if result.judgement == SampleJudgement.FAILED:
                failure_distribution["mismatch"] = failure_distribution.get("mismatch", 0) + 1
            elif result.judgement == SampleJudgement.RUNTIME_ERROR:
                key = result.error_code or "runtime_error"
                failure_distribution[key] = failure_distribution.get(key, 0) + 1

        self.job.status = EvalJobStatus.COMPLETED
        self.job.sample_count = len(sample_results)
        self.job.passed_count = passed_count
        self.job.failed_count = failed_count
        self.job.unscored_count = unscored_count
        self.job.runtime_error_count = runtime_error_count
        self.job.scored_count = scored_count
        self.job.pass_rate = round((passed_count / denominator) * 100, 2)
        self.job.failure_distribution = failure_distribution
        self.job.error_code = None
        self.job.error_message = None
        return self.job

    def mark_failed(self, error_code: str, error_message: str) -> EvalJobRecord:
        self.job.status = EvalJobStatus.FAILED
        self.job.error_code = error_code
        self.job.error_message = error_message
        return self.job
