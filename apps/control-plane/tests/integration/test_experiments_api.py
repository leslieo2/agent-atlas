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
        container.infrastructure.execution.model_runtime,
        "execute_published",
        execute_published,
    )


def _experiment_payload(
    *,
    name: str,
    dataset_version_id: str,
    tags: list[str],
    executor_backend: str = "local-runner",
    runner_mode: str | None = None,
) -> dict[str, object]:
    executor_config = {
        "backend": executor_backend,
        "timeout_seconds": 600,
        "max_steps": 32,
        "concurrency": 1,
        "resources": {},
        "tracing_backend": "phoenix",
        "artifact_path": None,
        "metadata": {},
    }
    if runner_mode is not None:
        executor_config["metadata"]["runner_mode"] = runner_mode

    return {
        "name": name,
        "spec": {
            "dataset_version_id": dataset_version_id,
            "published_agent_id": "basic",
            "model_config": {
                "model": "gpt-5.4-mini",
                "temperature": 0,
            },
            "prompt_config": {
                "prompt_version": "2026-03",
            },
            "toolset_config": {
                "tools": [],
                "metadata": {},
            },
            "evaluator_config": {
                "scoring_mode": "exact_match",
                "metadata": {},
            },
            "executor_config": executor_config,
            "tags": tags,
        },
    }


def test_experiments_api_supports_compare_and_run_curation(
    monkeypatch,
    client,
    worker_drain,
) -> None:
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "experiment-compare-dataset",
            "description": "Compare-ready experiment asset",
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
    dataset_version_id = dataset_response.json()["current_version_id"]

    _install_runtime(monkeypatch, outputs={"alpha": "alpha", "beta": "beta"})
    baseline_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="baseline",
            dataset_version_id=dataset_version_id,
            tags=["baseline"],
            runner_mode="in-process",
        ),
    )
    assert baseline_response.status_code == 201
    baseline_experiment_id = baseline_response.json()["experiment_id"]
    start_baseline = client.post(f"/api/v1/experiments/{baseline_experiment_id}/start")
    assert start_baseline.status_code == 200
    assert worker_drain(limit=40) >= 1

    _install_runtime(monkeypatch, outputs={"alpha": "alpha", "beta": "not-beta"})
    candidate_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="candidate",
            dataset_version_id=dataset_version_id,
            tags=["candidate"],
            runner_mode="in-process",
        ),
    )
    assert candidate_response.status_code == 201
    candidate_experiment_id = candidate_response.json()["experiment_id"]
    start_candidate = client.post(f"/api/v1/experiments/{candidate_experiment_id}/start")
    assert start_candidate.status_code == 200
    assert worker_drain(limit=40) >= 1

    detail_response = client.get(f"/api/v1/experiments/{candidate_experiment_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "completed"
    assert detail["sample_count"] == 2
    assert detail["completed_count"] == 2
    assert detail["passed_count"] == 1
    assert detail["failed_count"] == 1
    assert detail["pass_rate"] == pytest.approx(0.5, abs=0.01)

    runs_response = client.get(f"/api/v1/experiments/{candidate_experiment_id}/runs")
    assert runs_response.status_code == 200
    runs = {item["dataset_sample_id"]: item for item in runs_response.json()}
    assert runs["sample-pass"]["judgement"] == "passed"
    assert runs["sample-pass"]["slice"] == "shipping"
    assert runs["sample-pass"]["run_status"] == "succeeded"
    assert runs["sample-regressed"]["judgement"] == "failed"
    assert runs["sample-regressed"]["error_code"] == "mismatch"
    assert runs["sample-regressed"]["source"] == "crm"
    assert runs["sample-regressed"]["curation_status"] == "review"
    assert runs["sample-regressed"]["artifact_ref"]
    assert runs["sample-regressed"]["executor_backend"] == "local-runner"

    compare_response = client.get(
        "/api/v1/experiments/compare",
        params={
            "baseline_experiment_id": baseline_experiment_id,
            "candidate_experiment_id": candidate_experiment_id,
        },
    )
    assert compare_response.status_code == 200
    compare_payload = compare_response.json()
    assert compare_payload["dataset_version_id"] == dataset_version_id
    assert compare_payload["distribution"]["unchanged_pass"] == 1
    assert compare_payload["distribution"]["regressed"] == 1
    compare_samples = {item["dataset_sample_id"]: item for item in compare_payload["samples"]}
    assert compare_samples["sample-pass"]["compare_outcome"] == "unchanged_pass"
    assert compare_samples["sample-regressed"]["compare_outcome"] == "regressed"

    run_id = runs["sample-regressed"]["run_id"]
    patch_response = client.patch(
        f"/api/v1/experiments/{candidate_experiment_id}/runs/{run_id}",
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

    run_detail = client.get(f"/api/v1/runs/{run_id}")
    assert run_detail.status_code == 200
    assert run_detail.json()["experiment_id"] == candidate_experiment_id
