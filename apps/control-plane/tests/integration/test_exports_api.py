from __future__ import annotations

import json

from tests.integration.test_experiments_api import _experiment_payload, _install_runtime


def test_exports_api_creates_compare_aware_rl_rows(
    monkeypatch,
    client,
    worker_drain,
) -> None:
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "export-compare-dataset",
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
    assert client.post(f"/api/v1/experiments/{baseline_experiment_id}/start").status_code == 200
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
    assert client.post(f"/api/v1/experiments/{candidate_experiment_id}/start").status_code == 200
    assert worker_drain(limit=40) >= 1

    export_response = client.post(
        "/api/v1/exports",
        json={
            "baseline_experiment_id": baseline_experiment_id,
            "candidate_experiment_id": candidate_experiment_id,
            "compare_outcomes": ["regressed"],
            "format": "jsonl",
        },
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["row_count"] == 1
    assert export_payload["source_experiment_id"] == candidate_experiment_id
    assert export_payload["baseline_experiment_id"] == baseline_experiment_id
    assert export_payload["candidate_experiment_id"] == candidate_experiment_id
    assert export_payload["filters_summary"]["compare_outcomes"] == ["regressed"]

    history_response = client.get("/api/v1/exports")
    assert history_response.status_code == 200
    history = history_response.json()
    assert any(item["export_id"] == export_payload["export_id"] for item in history)

    download_response = client.get(f"/api/v1/exports/{export_payload['export_id']}")
    assert download_response.status_code == 200
    rows = [json.loads(line) for line in download_response.text.splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema_version"] == "rl-export-jsonl-v1"
    assert row["experiment_id"] == candidate_experiment_id
    assert row["dataset_version_id"] == dataset_version_id
    assert row["dataset_sample_id"] == "sample-regressed"
    assert row["compare_outcome"] == "regressed"
    assert row["dataset_slice"] == "returns"
    assert row["dataset_source"] == "crm"
    assert row["judgement"] == "failed"
    assert row["artifact_ref"]
    assert row["executor_backend"] == "local-runner"
    assert "published_agent_snapshot" in row
