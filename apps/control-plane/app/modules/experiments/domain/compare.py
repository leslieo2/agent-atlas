from __future__ import annotations

from collections import Counter

from app.modules.experiments.domain.models import (
    CandidateRunSummary,
    ExperimentCompareResult,
    ExperimentCompareSample,
    RunEvaluationRecord,
)
from app.modules.shared.domain.enums import CompareOutcome, SampleJudgement


def compare_outcome(
    baseline: RunEvaluationRecord | None,
    candidate: RunEvaluationRecord | None,
) -> CompareOutcome:
    if baseline is None:
        return CompareOutcome.CANDIDATE_ONLY
    if candidate is None:
        return CompareOutcome.BASELINE_ONLY
    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.UNCHANGED_PASS
    if (
        baseline.judgement != SampleJudgement.PASSED
        and candidate.judgement == SampleJudgement.PASSED
    ):
        return CompareOutcome.IMPROVED
    if (
        baseline.judgement == SampleJudgement.PASSED
        and candidate.judgement != SampleJudgement.PASSED
    ):
        return CompareOutcome.REGRESSED
    return CompareOutcome.UNCHANGED_FAIL


def build_compare_result(
    *,
    baseline_experiment_id,
    candidate_experiment_id,
    dataset_version_id,
    baseline_results: dict[str, RunEvaluationRecord],
    candidate_results: dict[str, RunEvaluationRecord],
) -> ExperimentCompareResult:
    sample_ids = sorted(set(baseline_results) | set(candidate_results))
    samples: list[ExperimentCompareSample] = []
    for sample_id in sample_ids:
        baseline_result = baseline_results.get(sample_id)
        candidate_result = candidate_results.get(sample_id)
        chosen = candidate_result or baseline_result
        outcome = compare_outcome(baseline_result, candidate_result)
        samples.append(
            ExperimentCompareSample(
                dataset_sample_id=sample_id,
                baseline_judgement=baseline_result.judgement if baseline_result else None,
                candidate_judgement=candidate_result.judgement if candidate_result else None,
                compare_outcome=outcome,
                error_code=(
                    candidate_result.error_code
                    if candidate_result and candidate_result.error_code
                    else baseline_result.error_code
                    if baseline_result
                    else None
                ),
                slice=chosen.slice if chosen else None,
                tags=list(chosen.tags) if chosen else [],
                candidate_run_summary=(
                    CandidateRunSummary(
                        run_id=candidate_result.run_id,
                        actual=candidate_result.actual,
                        trace_url=candidate_result.trace_url,
                    )
                    if candidate_result
                    else None
                ),
            )
        )
    distribution = Counter(sample.compare_outcome.value for sample in samples)
    return ExperimentCompareResult(
        baseline_experiment_id=baseline_experiment_id,
        candidate_experiment_id=candidate_experiment_id,
        dataset_version_id=dataset_version_id,
        distribution=dict(distribution),
        samples=samples,
    )
