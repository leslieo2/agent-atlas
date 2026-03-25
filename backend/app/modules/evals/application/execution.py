from __future__ import annotations

import random
from uuid import UUID

from app.modules.evals.application.ports import EvalJobRepository, EvaluatorPort
from app.modules.evals.domain.models import EvalJobCreate, EvalResult
from app.modules.evals.domain.policies import EvalJobAggregate


class EvalSampleEvaluator(EvaluatorPort):
    def evaluate(
        self,
        *,
        run_id: UUID,
        dataset: str,
        sample_index: int,
        rng: random.Random,
    ) -> EvalResult:
        result = EvalResult(
            sample_id=f"sample-{sample_index + 1}-{str(run_id)[:8]}",
            run_id=run_id,
            input=f"dataset sample #{sample_index + 1} from {dataset}",
            status="pass" if rng.random() > 0.4 else "fail",
            score=round(rng.uniform(0.45, 0.98), 2),
            reason=None,
        )
        if result.status == "fail":
            result.reason = "tool call mismatch or low judge score"
        return result


class EvalJobRecorder:
    def __init__(self, eval_job_repository: EvalJobRepository) -> None:
        self.eval_job_repository = eval_job_repository

    def mark_running(self, job_id: UUID) -> bool:
        job = self.eval_job_repository.get(job_id)
        if not job:
            return False
        self.eval_job_repository.save(EvalJobAggregate.load(job).mark_running())
        return True

    def append_result(self, job_id: UUID, result: EvalResult) -> bool:
        job = self.eval_job_repository.get(job_id)
        if not job:
            return False
        self.eval_job_repository.save(EvalJobAggregate.load(job).append_result(result))
        return True

    def mark_done(self, job_id: UUID) -> bool:
        job = self.eval_job_repository.get(job_id)
        if not job:
            return False
        self.eval_job_repository.save(EvalJobAggregate.load(job).mark_done())
        return True

    def mark_failed(self, job_id: UUID, reason: str) -> bool:
        job = self.eval_job_repository.get(job_id)
        if not job:
            return False
        self.eval_job_repository.save(EvalJobAggregate.load(job).mark_failed(reason))
        return True


class EvalJobRunner:
    def __init__(
        self,
        evaluator: EvaluatorPort | None = None,
        recorder: EvalJobRecorder | None = None,
    ) -> None:
        self.evaluator = evaluator or EvalSampleEvaluator()
        self.recorder = recorder

    def run(self, job_id: UUID, payload: EvalJobCreate) -> None:
        if self.recorder is None:
            raise RuntimeError("eval job recorder is not configured")

        random_seed = sum(int(run_id.int & 0xFFFFFFFF) for run_id in payload.run_ids) % 10000
        rng = random.Random(random_seed)  # nosec B311

        if not self.recorder.mark_running(job_id):
            return

        try:
            for index, run_id in enumerate(payload.run_ids):
                result = self.evaluator.evaluate(
                    run_id=run_id,
                    dataset=payload.dataset,
                    sample_index=index,
                    rng=rng,
                )
                if not self.recorder.append_result(job_id, result):
                    return
        except Exception as exc:
            self.recorder.mark_failed(job_id, str(exc))
            return

        self.recorder.mark_done(job_id)
