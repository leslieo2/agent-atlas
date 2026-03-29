from __future__ import annotations

from uuid import UUID

from app.modules.evals.domain.models import (
    EvalDatasetSample,
    EvalRunState,
    EvalSampleResult,
    SampleJudgement,
    ScoringMode,
)
from app.modules.shared.domain.enums import RunStatus


def evaluate_sample(
    sample: EvalDatasetSample,
    run: EvalRunState,
    scoring_mode: ScoringMode,
    *,
    eval_job_id: UUID | None = None,
) -> EvalSampleResult:
    expected = sample.expected.strip() if isinstance(sample.expected, str) else sample.expected
    actual = run.actual or ""
    resolved_eval_job_id = eval_job_id or UUID(int=0)

    if run.status in {RunStatus.FAILED, RunStatus.TERMINATED}:
        return EvalSampleResult(
            eval_job_id=resolved_eval_job_id,
            dataset_sample_id=sample.sample_id,
            run_id=run.run_id,
            judgement=SampleJudgement.RUNTIME_ERROR,
            input=sample.input,
            expected=sample.expected,
            actual=actual,
            failure_reason=(
                run.error_message or run.termination_reason or "runtime execution failed"
            ),
            error_code=run.error_code or "timeout_or_termination",
            trace_url=run.trace_url,
            tags=sample.tags,
        )

    if expected is None or expected == "":
        return EvalSampleResult(
            eval_job_id=resolved_eval_job_id,
            dataset_sample_id=sample.sample_id,
            run_id=run.run_id,
            judgement=SampleJudgement.UNSCORED,
            input=sample.input,
            expected=sample.expected,
            actual=actual,
            trace_url=run.trace_url,
            tags=sample.tags,
        )

    if scoring_mode == ScoringMode.EXACT_MATCH:
        matched = actual == expected
        failure_reason = None if matched else "actual output did not exactly match expected output"
    else:
        matched = expected in actual
        failure_reason = None if matched else "actual output did not contain expected text"

    return EvalSampleResult(
        eval_job_id=resolved_eval_job_id,
        dataset_sample_id=sample.sample_id,
        run_id=run.run_id,
        judgement=SampleJudgement.PASSED if matched else SampleJudgement.FAILED,
        input=sample.input,
        expected=sample.expected,
        actual=actual,
        failure_reason=failure_reason,
        trace_url=run.trace_url,
        tags=sample.tags,
    )
