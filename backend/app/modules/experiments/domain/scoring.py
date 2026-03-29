from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from app.modules.experiments.domain.models import RunEvaluationRecord
from app.modules.shared.domain.enums import CurationStatus, RunStatus, SampleJudgement, ScoringMode


class EvaluatedSample(Protocol):
    sample_id: str
    input: str
    expected: str | None
    tags: list[str]
    slice: str | None
    source: str | None
    metadata: dict[str, Any] | None
    export_eligible: bool | None


class EvaluatedRun(Protocol):
    run_id: Any
    status: RunStatus
    error_message: str | None
    termination_reason: str | None
    error_code: str | None
    trace_pointer: Any
    provenance: Any
    artifact_ref: str | None
    image_ref: str | None
    executor_backend: str | None
    latency_ms: int
    tool_calls: int
    container_image: str | None


class TrajectoryLike(Protocol):
    output: str | None
    model: str | None


def evaluate_run(
    *,
    experiment_id,
    dataset_version_id,
    sample: EvaluatedSample,
    run: EvaluatedRun,
    trajectory: Sequence[Any],
    scoring_mode: ScoringMode,
) -> RunEvaluationRecord:
    expected = sample.expected.strip() if isinstance(sample.expected, str) else sample.expected
    actual = trajectory[-1].output if trajectory else None
    default_export_eligible = (
        sample.export_eligible
        if sample.export_eligible is not None
        else run.status not in {RunStatus.CANCELLED, RunStatus.LOST}
    )

    if run.status in {RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.LOST}:
        return RunEvaluationRecord(
            experiment_id=experiment_id,
            dataset_version_id=dataset_version_id,
            dataset_sample_id=sample.sample_id,
            run_id=run.run_id,
            judgement=SampleJudgement.RUNTIME_ERROR,
            input=sample.input,
            expected=sample.expected,
            actual=actual,
            failure_reason=run.error_message
            or run.termination_reason
            or "runtime execution failed",
            error_code=run.error_code or "timeout_or_cancellation",
            error_message=run.error_message,
            trace_url=run.trace_pointer.trace_url if run.trace_pointer else None,
            tags=sample.tags,
            slice=sample.slice,
            source=sample.source,
            metadata=sample.metadata,
            export_eligible=default_export_eligible,
            curation_status=CurationStatus.REVIEW,
            published_agent_snapshot=run.provenance.published_agent_snapshot
            if run.provenance
            else None,
            artifact_ref=run.provenance.artifact_ref if run.provenance else run.artifact_ref,
            image_ref=run.provenance.image_ref if run.provenance else run.image_ref,
            executor_backend=run.executor_backend,
            framework=run.provenance.framework if run.provenance else None,
            latency_ms=run.latency_ms,
            tool_calls=run.tool_calls,
            prompt_version=trajectory[-1].model if trajectory else None,
            image_digest=run.container_image,
            run_status=run.status,
        )

    if expected is None or expected == "":
        return RunEvaluationRecord(
            experiment_id=experiment_id,
            dataset_version_id=dataset_version_id,
            dataset_sample_id=sample.sample_id,
            run_id=run.run_id,
            judgement=SampleJudgement.UNSCORED,
            input=sample.input,
            expected=sample.expected,
            actual=actual,
            trace_url=run.trace_pointer.trace_url if run.trace_pointer else None,
            tags=sample.tags,
            slice=sample.slice,
            source=sample.source,
            metadata=sample.metadata,
            export_eligible=default_export_eligible,
            curation_status=CurationStatus.REVIEW,
            published_agent_snapshot=run.provenance.published_agent_snapshot
            if run.provenance
            else None,
            artifact_ref=run.provenance.artifact_ref if run.provenance else run.artifact_ref,
            image_ref=run.provenance.image_ref if run.provenance else run.image_ref,
            executor_backend=run.executor_backend,
            framework=run.provenance.framework if run.provenance else None,
            latency_ms=run.latency_ms,
            tool_calls=run.tool_calls,
            image_digest=run.container_image,
            run_status=run.status,
        )

    resolved_actual = actual or ""
    if scoring_mode == ScoringMode.EXACT_MATCH:
        matched = resolved_actual == expected
        failure_reason = None if matched else "actual output did not exactly match expected output"
    else:
        matched = expected in resolved_actual
        failure_reason = None if matched else "actual output did not contain expected text"

    return RunEvaluationRecord(
        experiment_id=experiment_id,
        dataset_version_id=dataset_version_id,
        dataset_sample_id=sample.sample_id,
        run_id=run.run_id,
        judgement=SampleJudgement.PASSED if matched else SampleJudgement.FAILED,
        input=sample.input,
        expected=sample.expected,
        actual=actual,
        failure_reason=failure_reason,
        error_code=None if matched else "mismatch",
        trace_url=run.trace_pointer.trace_url if run.trace_pointer else None,
        tags=sample.tags,
        slice=sample.slice,
        source=sample.source,
        metadata=sample.metadata,
        export_eligible=default_export_eligible,
        curation_status=CurationStatus.INCLUDE if matched else CurationStatus.REVIEW,
        published_agent_snapshot=run.provenance.published_agent_snapshot
        if run.provenance
        else None,
        artifact_ref=run.provenance.artifact_ref if run.provenance else run.artifact_ref,
        image_ref=run.provenance.image_ref if run.provenance else run.image_ref,
        executor_backend=run.executor_backend,
        framework=run.provenance.framework if run.provenance else None,
        latency_ms=run.latency_ms,
        tool_calls=run.tool_calls,
        image_digest=run.container_image,
        run_status=run.status,
    )
