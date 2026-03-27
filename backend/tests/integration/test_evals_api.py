from __future__ import annotations

from uuid import uuid4

import pytest
from app.bootstrap.container import get_container
from app.core.errors import ProviderAuthError
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult


def test_eval_jobs_api_fans_out_child_runs_and_aggregates_results(
    monkeypatch,
    client,
    worker_drain,
):
    container = get_container()

    def execute_published(_run_id, payload):
        if payload.prompt == "runtime":
            raise ProviderAuthError("provider authentication failed")

        output = {
            "alpha": "alpha",
            "beta": "not-beta",
            "gamma": "gamma",
        }.get(payload.prompt, payload.prompt)

        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output=output,
                latency_ms=3,
                token_usage=5,
                provider="mock",
                resolved_model="gpt-4.1-mini",
            )
        )

    monkeypatch.setattr(container.model_runtime, "execute_published", execute_published)

    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "eval-dataset",
            "rows": [
                {"sample_id": "sample-pass", "input": "alpha", "expected": "alpha"},
                {"sample_id": "sample-fail", "input": "beta", "expected": "beta"},
                {"sample_id": "sample-unscored", "input": "gamma", "expected": None},
                {"sample_id": "sample-runtime", "input": "runtime", "expected": "runtime"},
            ],
        },
    )
    assert dataset_response.status_code == 200

    response = client.post(
        "/api/v1/eval-jobs",
        json={
            "agent_id": "basic",
            "dataset": "eval-dataset",
            "project": "nightly-regression",
            "tags": ["nightly", "smoke"],
            "scoring_mode": "exact_match",
        },
    )

    assert response.status_code == 201
    created = response.json()
    eval_job_id = created["eval_job_id"]
    assert created["status"] == "queued"
    assert created["sample_count"] == 4
    assert created["passed_count"] == 0

    assert worker_drain(limit=20) >= 1

    detail = client.get(f"/api/v1/eval-jobs/{eval_job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "completed"
    assert payload["sample_count"] == 4
    assert payload["passed_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["unscored_count"] == 1
    assert payload["runtime_error_count"] == 1
    assert payload["scored_count"] == 3
    assert payload["pass_rate"] == pytest.approx(33.33, abs=0.01)
    assert payload["failure_distribution"] == {
        "mismatch": 1,
        "provider_call": 1,
    }

    listing = client.get("/api/v1/eval-jobs")
    assert listing.status_code == 200
    assert listing.json()[0]["eval_job_id"] == eval_job_id

    samples_response = client.get(f"/api/v1/eval-jobs/{eval_job_id}/samples")
    assert samples_response.status_code == 200
    samples = {item["dataset_sample_id"]: item for item in samples_response.json()}

    assert samples["sample-pass"]["judgement"] == "passed"
    assert samples["sample-fail"]["judgement"] == "failed"
    assert (
        samples["sample-fail"]["failure_reason"]
        == "actual output did not exactly match expected output"
    )
    assert samples["sample-unscored"]["judgement"] == "unscored"
    assert samples["sample-runtime"]["judgement"] == "runtime_error"
    assert samples["sample-runtime"]["error_code"] == "provider_call"
    assert all(item["run_id"] for item in samples.values())

    runs = client.get("/api/v1/runs").json()
    eval_runs = [item for item in runs if item.get("eval_job_id") == eval_job_id]
    assert len(eval_runs) == 4
    assert {item["dataset_sample_id"] for item in eval_runs} == {
        "sample-pass",
        "sample-fail",
        "sample-unscored",
        "sample-runtime",
    }


def test_eval_jobs_api_supports_contains_scoring(monkeypatch, client, worker_drain):
    container = get_container()

    monkeypatch.setattr(
        container.model_runtime,
        "execute_published",
        lambda _run_id, payload: PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output=f"prefix::{payload.prompt}::suffix",
                latency_ms=2,
                token_usage=4,
                provider="mock",
                resolved_model="gpt-4.1-mini",
            )
        ),
    )

    dataset_name = f"eval-contains-{uuid4().hex[:8]}"
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": dataset_name,
            "rows": [
                {"sample_id": "contains-pass", "input": "needle", "expected": "needle"},
            ],
        },
    )
    assert dataset_response.status_code == 200

    response = client.post(
        "/api/v1/eval-jobs",
        json={
            "agent_id": "basic",
            "dataset": dataset_name,
            "project": "contains-regression",
            "tags": [],
            "scoring_mode": "contains",
        },
    )
    assert response.status_code == 201

    assert worker_drain(limit=10) >= 1

    detail = client.get(f"/api/v1/eval-jobs/{response.json()['eval_job_id']}")
    assert detail.status_code == 200
    assert detail.json()["passed_count"] == 1
