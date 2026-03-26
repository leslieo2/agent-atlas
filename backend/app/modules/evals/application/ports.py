from __future__ import annotations

import random
from typing import Protocol
from uuid import UUID

from app.modules.evals.domain.models import EvalJob, EvalResult
from app.modules.runs.domain.models import RunRecord


class EvalJobRepository(Protocol):
    def get(self, job_id: str | UUID) -> EvalJob | None: ...

    def save(self, job: EvalJob) -> None: ...


class EvalRunReader(Protocol):
    def get(self, run_id: str | UUID) -> RunRecord | None: ...


class EvaluatorPort(Protocol):
    def evaluate(
        self,
        *,
        run_id: UUID,
        dataset: str,
        sample_index: int,
        rng: random.Random,
    ) -> EvalResult: ...
