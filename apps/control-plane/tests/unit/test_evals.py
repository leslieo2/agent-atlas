from __future__ import annotations

from uuid import uuid4

from app.modules.evals.domain.models import (
    EvalDatasetSample,
    EvalRunState,
    SampleJudgement,
    ScoringMode,
)
from app.modules.evals.domain.scoring import evaluate_sample
from app.modules.shared.domain.enums import RunStatus


def test_evaluate_sample_exact_match_passes() -> None:
    sample = EvalDatasetSample(sample_id="sample-pass", input="hello", expected="hello")
    run = EvalRunState(
        run_id=uuid4(),
        dataset_sample_id="sample-pass",
        status=RunStatus.SUCCEEDED,
        actual="hello",
    )

    result = evaluate_sample(sample=sample, run=run, scoring_mode=ScoringMode.EXACT_MATCH)

    assert result.judgement == SampleJudgement.PASSED
    assert result.failure_reason is None
    assert result.actual == "hello"


def test_evaluate_sample_contains_marks_failed_when_expected_is_missing_from_output() -> None:
    sample = EvalDatasetSample(sample_id="sample-fail", input="hello", expected="agent atlas")
    run = EvalRunState(
        run_id=uuid4(),
        dataset_sample_id="sample-fail",
        status=RunStatus.SUCCEEDED,
        actual="hello world",
    )

    result = evaluate_sample(sample=sample, run=run, scoring_mode=ScoringMode.CONTAINS)

    assert result.judgement == SampleJudgement.FAILED
    assert result.failure_reason == "actual output did not contain expected text"


def test_evaluate_sample_marks_expected_none_as_unscored() -> None:
    sample = EvalDatasetSample(sample_id="sample-unscored", input="hello", expected=None)
    run = EvalRunState(
        run_id=uuid4(),
        dataset_sample_id="sample-unscored",
        status=RunStatus.SUCCEEDED,
        actual="anything",
    )

    result = evaluate_sample(sample=sample, run=run, scoring_mode=ScoringMode.EXACT_MATCH)

    assert result.judgement == SampleJudgement.UNSCORED
    assert result.failure_reason is None


def test_evaluate_sample_maps_runtime_failures_without_scoring() -> None:
    sample = EvalDatasetSample(sample_id="sample-runtime", input="hello", expected="hello")
    run = EvalRunState(
        run_id=uuid4(),
        dataset_sample_id="sample-runtime",
        status=RunStatus.FAILED,
        actual="",
        error_code="provider_call",
        error_message="provider authentication failed",
        termination_reason="provider authentication failed",
    )

    result = evaluate_sample(sample=sample, run=run, scoring_mode=ScoringMode.EXACT_MATCH)

    assert result.judgement == SampleJudgement.RUNTIME_ERROR
    assert result.failure_reason == "provider authentication failed"
    assert result.error_code == "provider_call"
