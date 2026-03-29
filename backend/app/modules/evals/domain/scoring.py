from __future__ import annotations

from uuid import UUID

from app.modules.evals.domain.models import (
    CurationStatus,
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
    default_export_eligible = (
        sample.export_eligible
        if sample.export_eligible is not None
        else run.status not in {RunStatus.CANCELLED, RunStatus.LOST}
    )

    if run.status in {RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.LOST}:
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
            error_code=run.error_code or "timeout_or_cancellation",
            error_message=run.error_message,
            trace_url=run.trace_url,
            tags=sample.tags,
            slice=sample.slice,
            source=sample.source,
            metadata=sample.metadata,
            export_eligible=default_export_eligible,
            curation_status=CurationStatus.REVIEW,
            published_agent_snapshot=run.published_agent_snapshot,
            artifact_ref=run.artifact_ref,
            image_ref=run.image_ref,
            runner_backend=run.runner_backend,
            framework=run.framework,
            latency_ms=run.latency_ms,
            tool_calls=run.tool_calls,
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
            slice=sample.slice,
            source=sample.source,
            metadata=sample.metadata,
            export_eligible=default_export_eligible,
            curation_status=CurationStatus.REVIEW,
            published_agent_snapshot=run.published_agent_snapshot,
            artifact_ref=run.artifact_ref,
            image_ref=run.image_ref,
            runner_backend=run.runner_backend,
            framework=run.framework,
            latency_ms=run.latency_ms,
            tool_calls=run.tool_calls,
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
        error_code=None if matched else "mismatch",
        trace_url=run.trace_url,
        tags=sample.tags,
        slice=sample.slice,
        source=sample.source,
        metadata=sample.metadata,
        export_eligible=default_export_eligible,
        curation_status=CurationStatus.INCLUDE if matched else CurationStatus.REVIEW,
        published_agent_snapshot=run.published_agent_snapshot,
        artifact_ref=run.artifact_ref,
        image_ref=run.image_ref,
        runner_backend=run.runner_backend,
        framework=run.framework,
        latency_ms=run.latency_ms,
        tool_calls=run.tool_calls,
    )
