from __future__ import annotations

from app.modules.evals.domain.models import EvalJob, EvalResult
from app.modules.shared.domain.enums import EvalStatus


class EvalJobAggregate:
    def __init__(self, job: EvalJob) -> None:
        self.job = job

    @classmethod
    def load(cls, job: EvalJob) -> EvalJobAggregate:
        return cls(job)

    def mark_running(self) -> EvalJob:
        if self.job.status != EvalStatus.QUEUED:
            raise ValueError(f"cannot start eval job from status={self.job.status.value}")
        self.job.status = EvalStatus.RUNNING
        self.job.failure_reason = None
        return self.job

    def append_result(self, result: EvalResult) -> EvalJob:
        if self.job.status not in {EvalStatus.QUEUED, EvalStatus.RUNNING}:
            raise ValueError(f"cannot append results from status={self.job.status.value}")
        self.job.results.append(result)
        return self.job

    def mark_done(self) -> EvalJob:
        if self.job.status not in {EvalStatus.QUEUED, EvalStatus.RUNNING}:
            raise ValueError(f"cannot complete eval job from status={self.job.status.value}")
        self.job.status = EvalStatus.DONE
        self.job.failure_reason = None
        return self.job

    def mark_failed(self, reason: str) -> EvalJob:
        self.job.status = EvalStatus.FAILED
        self.job.failure_reason = reason
        return self.job
