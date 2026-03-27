from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.datasets.domain.models import Dataset, DatasetSample
from app.modules.evals.domain.models import EvalJobRecord, EvalRunState, EvalSampleResult


class EvalJobRepository(Protocol):
    def get(self, eval_job_id: str | UUID) -> EvalJobRecord | None: ...

    def list(self) -> list[EvalJobRecord]: ...

    def save(self, job: EvalJobRecord) -> None: ...


class EvalSampleResultRepository(Protocol):
    def list_for_job(self, eval_job_id: str | UUID) -> list[EvalSampleResult]: ...

    def save(self, result: EvalSampleResult) -> None: ...

    def delete_for_job(self, eval_job_id: str | UUID) -> None: ...


class DatasetSourcePort(Protocol):
    def get(self, name: str) -> Dataset | None: ...


class AgentLookupPort(Protocol):
    def exists(self, agent_id: str) -> bool: ...


class EvalRunGatewayPort(Protocol):
    def create_eval_run(self, job: EvalJobRecord, sample: DatasetSample) -> UUID: ...

    def list_eval_runs(self, eval_job_id: str | UUID) -> list[EvalRunState]: ...
