from __future__ import annotations

import random
import threading
from uuid import UUID

from app.db.state import state
from app.models.schemas import EvalJob, EvalJobCreate, EvalResult, EvalStatus


class EvalService:
    def create_job(self, payload: EvalJobCreate) -> EvalJob:
        job = EvalJob(run_ids=payload.run_ids, dataset=payload.dataset)
        with state.lock:
            state.eval_jobs[job.job_id] = job
            state.save_eval_job(job)
        threading.Thread(target=self._run_job, args=(job.job_id, payload), daemon=True).start()
        return job

    def get_job(self, job_id: str | UUID) -> EvalJob | None:
        job_uuid = self._coerce_id(job_id)
        with state.lock:
            return state.eval_jobs.get(job_uuid)

    def _run_job(self, job_id: UUID, payload: EvalJobCreate) -> None:
        random_seed = sum(int(x.int & 0xFFFFFFFF) for x in payload.run_ids) % 10000
        rng = random.Random(random_seed)
        with state.lock:
            state.eval_jobs[job_id].status = EvalStatus.RUNNING
            state.save_eval_job(state.eval_jobs[job_id])
        for idx, rid in enumerate(payload.run_ids):
            status = "pass" if rng.random() > 0.4 else "fail"
            score = round(rng.uniform(0.45, 0.98), 2)
            reason = None if status == "pass" else "tool call mismatch or low judge score"
            result = EvalResult(
                sample_id=f"sample-{idx+1}-{str(rid)[:8]}",
                run_id=rid,
                input=f"dataset sample #{idx+1} from {payload.dataset}",
                status=status,
                score=score,
                reason=reason,
            )
            with state.lock:
                if job_id in state.eval_jobs:
                    state.eval_jobs[job_id].results.append(result)
                    state.save_eval_job(state.eval_jobs[job_id])
        with state.lock:
            if job_id in state.eval_jobs:
                state.eval_jobs[job_id].status = EvalStatus.DONE
                state.save_eval_job(state.eval_jobs[job_id])

    @staticmethod
    def _coerce_id(value: str | UUID) -> UUID:
        if isinstance(value, str):
            return UUID(value)
        return value


eval_service = EvalService()
