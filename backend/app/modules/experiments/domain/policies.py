from __future__ import annotations

from collections import Counter

from app.modules.experiments.domain.models import (
    ExperimentCreateInput,
    ExperimentRecord,
    ExperimentStatus,
    RunEvaluationRecord,
)
from app.modules.shared.domain.enums import SampleJudgement


class ExperimentAggregate:
    def __init__(self, experiment: ExperimentRecord) -> None:
        self.experiment = experiment

    @classmethod
    def create(
        cls, payload: ExperimentCreateInput, *, dataset_name: str, sample_count: int
    ) -> ExperimentRecord:
        return ExperimentRecord(
            name=payload.name,
            dataset_name=dataset_name,
            dataset_version_id=payload.spec.dataset_version_id,
            published_agent_id=payload.spec.published_agent_id,
            status=ExperimentStatus.DRAFT,
            tags=list(payload.spec.tags),
            spec=payload.spec.model_copy(deep=True),
            sample_count=sample_count,
        )

    @classmethod
    def load(cls, experiment: ExperimentRecord) -> ExperimentAggregate:
        return cls(experiment)

    def queue(self) -> ExperimentRecord:
        if self.experiment.status not in {ExperimentStatus.DRAFT, ExperimentStatus.FAILED}:
            raise ValueError(f"cannot queue experiment from status={self.experiment.status.value}")
        self.experiment.status = ExperimentStatus.QUEUED
        self.experiment.error_code = None
        self.experiment.error_message = None
        return self.experiment

    def mark_running(self) -> ExperimentRecord:
        if self.experiment.status not in {
            ExperimentStatus.QUEUED,
            ExperimentStatus.DRAFT,
        }:
            raise ValueError(f"cannot run experiment from status={self.experiment.status.value}")
        self.experiment.status = ExperimentStatus.RUNNING
        return self.experiment

    def mark_cancelled(self) -> ExperimentRecord:
        if self.experiment.status in {ExperimentStatus.COMPLETED, ExperimentStatus.CANCELLED}:
            raise ValueError(f"cannot cancel experiment from status={self.experiment.status.value}")
        self.experiment.status = ExperimentStatus.CANCELLED
        return self.experiment

    def mark_failed(self, error_code: str, error_message: str) -> ExperimentRecord:
        self.experiment.status = ExperimentStatus.FAILED
        self.experiment.error_code = error_code
        self.experiment.error_message = error_message
        return self.experiment

    def complete(self, results: list[RunEvaluationRecord]) -> ExperimentRecord:
        counts = Counter(result.judgement.value for result in results)
        failures = Counter(
            result.error_code or "unknown" for result in results if result.error_code
        )
        scored = counts.get(SampleJudgement.PASSED.value, 0) + counts.get(
            SampleJudgement.FAILED.value, 0
        )
        pass_rate = counts.get(SampleJudgement.PASSED.value, 0) / scored if scored else 0.0
        self.experiment.status = ExperimentStatus.COMPLETED
        self.experiment.completed_count = len(results)
        self.experiment.passed_count = counts.get(SampleJudgement.PASSED.value, 0)
        self.experiment.failed_count = counts.get(SampleJudgement.FAILED.value, 0)
        self.experiment.unscored_count = counts.get(SampleJudgement.UNSCORED.value, 0)
        self.experiment.runtime_error_count = counts.get(SampleJudgement.RUNTIME_ERROR.value, 0)
        self.experiment.pass_rate = pass_rate
        self.experiment.failure_distribution = dict(failures)
        self.experiment.error_code = None
        self.experiment.error_message = None
        return self.experiment
