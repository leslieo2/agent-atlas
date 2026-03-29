from __future__ import annotations

import pytest
from app.bootstrap.container import get_container
from app.core.errors import ProviderAuthError
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult


def _install_runtime(
    monkeypatch,
    outputs: dict[str, str],
    failures: set[str] | None = None,
) -> None:
    container = get_container()
    failing_prompts = failures or set()

    def execute_published(_run_id, payload):
        if payload.prompt in failing_prompts:
            raise ProviderAuthError("provider authentication failed")

        output = outputs.get(payload.prompt, payload.prompt)
        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output=output,
                latency_ms=3,
                token_usage=5,
                provider="mock",
                resolved_model="gpt-5.4-mini",
            )
        )

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )


def test_eval_jobs_api_supports_compare_and_sample_curation(
    monkeypatch,
    client,
    worker_drain,
) -> None:
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "eval-compare-dataset",
            "description": "Compare-ready eval asset",
            "source": "crm",
            "version": "2026-03",
            "rows": [
                {
                    "sample_id": "sample-pass",
                    "input": "alpha",
                    "expected": "alpha",
                    "tags": ["shipping"],
                    "slice": "shipping",
                    "source": "crm",
                    "export_eligible": True,
                },
                {
                    "sample_id": "sample-regressed",
                    "input": "beta",
                    "expected": "beta",
                    "tags": ["returns"],
                    "slice": "returns",
                    "source": "crm",
                    "export_eligible": True,
                },
            ],
        },
    )
    assert dataset_response.status_code == 200

    _install_runtime(monkeypatch, outputs={"alpha": "alpha", "beta": "beta"})
    baseline_response = client.post(
        "/api/v1/eval-jobs",
        json={
            "agent_id": "basic",
            "dataset": "eval-compare-dataset",
            "project": "rl-eval",
            "tags": ["baseline"],
            "scoring_mode": "exact_match",
        },
    )
    assert baseline_response.status_code == 201
    baseline_eval_job_id = baseline_response.json()["eval_job_id"]
    assert worker_drain(limit=20) >= 1

    _install_runtime(monkeypatch, outputs={"alpha": "alpha", "beta": "not-beta"})
    candidate_response = client.post(
        "/api/v1/eval-jobs",
        json={
            "agent_id": "basic",
            "dataset": "eval-compare-dataset",
            "project": "rl-eval",
            "tags": ["candidate"],
            "scoring_mode": "exact_match",
        },
    )
    assert candidate_response.status_code == 201
    candidate_eval_job_id = candidate_response.json()["eval_job_id"]
    assert worker_drain(limit=20) >= 1

    detail_response = client.get(f"/api/v1/eval-jobs/{candidate_eval_job_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "completed"
    assert detail["sample_count"] == 2
    assert detail["passed_count"] == 1
    assert detail["failed_count"] == 1
    assert detail["pass_rate"] == pytest.approx(50.0, abs=0.01)

    samples_response = client.get(f"/api/v1/eval-jobs/{candidate_eval_job_id}/samples")
    assert samples_response.status_code == 200
    samples = {item["dataset_sample_id"]: item for item in samples_response.json()}
    assert samples["sample-pass"]["judgement"] == "passed"
    assert samples["sample-pass"]["slice"] == "shipping"
    assert samples["sample-regressed"]["judgement"] == "failed"
    assert samples["sample-regressed"]["error_code"] == "mismatch"
    assert samples["sample-regressed"]["source"] == "crm"
    assert samples["sample-regressed"]["curation_status"] == "review"
    assert samples["sample-regressed"]["artifact_ref"]
    assert samples["sample-regressed"]["runner_backend"]

    compare_response = client.get(
        "/api/v1/eval-jobs/compare",
        params={
            "baseline_eval_job_id": baseline_eval_job_id,
            "candidate_eval_job_id": candidate_eval_job_id,
        },
    )
    assert compare_response.status_code == 200
    compare_payload = compare_response.json()
    assert compare_payload["dataset"] == "eval-compare-dataset"
    assert compare_payload["distribution"]["unchanged_pass"] == 1
    assert compare_payload["distribution"]["regressed"] == 1
    compare_samples = {item["dataset_sample_id"]: item for item in compare_payload["samples"]}
    assert compare_samples["sample-pass"]["compare_outcome"] == "unchanged_pass"
    assert compare_samples["sample-regressed"]["compare_outcome"] == "regressed"

    patch_response = client.patch(
        f"/api/v1/eval-jobs/{candidate_eval_job_id}/samples/sample-regressed",
        json={
            "curation_status": "exclude",
            "curation_note": "environment noise",
            "export_eligible": False,
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["curation_status"] == "exclude"
    assert patched["curation_note"] == "environment noise"
    assert patched["export_eligible"] is False

    sample_detail = client.get(
        f"/api/v1/eval-jobs/{candidate_eval_job_id}/samples/sample-regressed"
    )
    assert sample_detail.status_code == 200
    assert sample_detail.json()["curation_status"] == "exclude"
