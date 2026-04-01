from __future__ import annotations

import json

from tests.integration.test_experiments_api import _experiment_payload, _install_runtime
from tests.support.fake_k8s import install_fake_k8s_runtime


def _drain_background_work(worker_drain, *, limit: int, rounds: int = 5) -> int:
    processed_total = 0
    for _ in range(rounds):
        processed = worker_drain(limit=limit)
        processed_total += processed
        if processed == 0:
            break
    return processed_total


def test_exports_api_creates_compare_aware_rl_rows(
    monkeypatch,
    client,
    worker_drain,
    wait_until,
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
            executor_backend="local-runner",
            runner_mode="in-process",
        ),
    )
    assert baseline_response.status_code == 201
    baseline_experiment_id = baseline_response.json()["experiment_id"]
    assert client.post(f"/api/v1/experiments/{baseline_experiment_id}/start").status_code == 200
    assert _drain_background_work(worker_drain, limit=40, rounds=6) >= 1

    _install_runtime(monkeypatch, outputs={"alpha": "alpha", "beta": "not-beta"})
    candidate_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="candidate",
            dataset_version_id=dataset_version_id,
            tags=["candidate"],
            executor_backend="local-runner",
            runner_mode="in-process",
        ),
    )
    assert candidate_response.status_code == 201
    candidate_experiment_id = candidate_response.json()["experiment_id"]
    assert client.post(f"/api/v1/experiments/{candidate_experiment_id}/start").status_code == 200
    assert _drain_background_work(worker_drain, limit=40, rounds=6) >= 1
    wait_until(
        lambda: client.get(f"/api/v1/experiments/{candidate_experiment_id}").json()["status"]
        == "completed"
    )

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


def test_k8s_experiment_loop_recovers_trace_artifacts_and_export_chain(
    monkeypatch,
    client,
    worker_drain,
    wait_until,
    tmp_path,
) -> None:
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "k8s-export-dataset",
            "source": "crm",
            "version": "2026-04",
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

    runner_image = "ghcr.io/example/atlas-runner:latest"
    baseline_artifacts = tmp_path / "baseline-artifacts"
    candidate_artifacts = tmp_path / "candidate-artifacts"

    install_fake_k8s_runtime(
        monkeypatch,
        outputs={"alpha": "alpha", "beta": "beta"},
        artifact_contents={"alpha": "baseline alpha", "beta": "baseline beta"},
    )
    baseline_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="baseline-k8s",
            dataset_version_id=dataset_version_id,
            tags=["baseline", "k8s"],
            executor_backend="k8s-job",
            executor_overrides={
                "runner_image": runner_image,
                "artifact_path": str(baseline_artifacts),
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            },
        ),
    )
    assert baseline_response.status_code == 201
    baseline_experiment_id = baseline_response.json()["experiment_id"]
    assert client.post(f"/api/v1/experiments/{baseline_experiment_id}/start").status_code == 200
    assert _drain_background_work(worker_drain, limit=80, rounds=8) >= 1

    install_fake_k8s_runtime(
        monkeypatch,
        outputs={"alpha": "alpha", "beta": "not-beta"},
        artifact_contents={"alpha": "candidate alpha", "beta": "candidate beta"},
    )
    candidate_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="candidate-k8s",
            dataset_version_id=dataset_version_id,
            tags=["candidate", "k8s"],
            executor_backend="k8s-job",
            executor_overrides={
                "runner_image": runner_image,
                "artifact_path": str(candidate_artifacts),
                "metadata": {"command": ["python", "-m", "atlas_runner"]},
            },
        ),
    )
    assert candidate_response.status_code == 201
    candidate_experiment_id = candidate_response.json()["experiment_id"]
    assert client.post(f"/api/v1/experiments/{candidate_experiment_id}/start").status_code == 200
    assert _drain_background_work(worker_drain, limit=80, rounds=8) >= 1
    wait_until(
        lambda: client.get(f"/api/v1/experiments/{candidate_experiment_id}").json()["status"]
        == "completed",
        timeout=5.0,
    )

    detail_response = client.get(f"/api/v1/experiments/{candidate_experiment_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "completed"

    runs_response = client.get(f"/api/v1/experiments/{candidate_experiment_id}/runs")
    assert runs_response.status_code == 200
    runs = {item["dataset_sample_id"]: item for item in runs_response.json()}
    assert runs["sample-pass"]["judgement"] == "passed"
    assert runs["sample-regressed"]["judgement"] == "failed"
    assert runs["sample-regressed"]["trace_url"] is not None
    assert runs["sample-regressed"]["trace_url"].startswith("http://phoenix.test:6006/projects/")
    assert runs["sample-regressed"]["executor_backend"] == "k8s-job"
    assert runs["sample-regressed"]["tool_calls"] == 0

    run_id = runs["sample-regressed"]["run_id"]
    run_detail_response = client.get(f"/api/v1/runs/{run_id}")
    assert run_detail_response.status_code == 200
    run_detail = run_detail_response.json()
    assert run_detail["status"] == "succeeded"
    assert run_detail["runner_backend"] == "k8s-container"
    assert run_detail["execution_backend"] == "kubernetes-job"
    assert run_detail["container_image"] == runner_image
    assert run_detail["trace_pointer"]["trace_url"] == runs["sample-regressed"]["trace_url"]
    assert run_detail["trace_pointer"]["project_url"].startswith(
        "http://phoenix.test:6006/projects/"
    )

    artifact_file = (
        candidate_artifacts
        / run_detail["run_id"]
        / run_detail["attempt_id"]
        / "artifacts"
        / "reports"
        / "summary.txt"
    )
    assert artifact_file.read_text(encoding="utf-8") == "candidate beta"

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

    download_response = client.get(f"/api/v1/exports/{export_payload['export_id']}")
    assert download_response.status_code == 200
    rows = [json.loads(line) for line in download_response.text.splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["dataset_sample_id"] == "sample-regressed"
    assert row["actual"] == "not-beta"
    assert row["compare_outcome"] == "regressed"
    assert row["executor_backend"] == "k8s-job"
    assert row["artifact_ref"]
    assert row["trace_url"] == runs["sample-regressed"]["trace_url"]


def test_claude_code_cli_experiment_loop_runs_on_external_runner_k8s_carrier(
    monkeypatch,
    client,
    worker_drain,
    wait_until,
    tmp_path,
) -> None:
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "claude-code-export-dataset",
            "source": "crm",
            "version": "2026-04",
            "rows": [
                {
                    "sample_id": "sample-pass",
                    "input": "alpha",
                    "expected": "alpha",
                    "tags": ["shipping"],
                    "slice": "shipping",
                    "source": "crm",
                    "export_eligible": True,
                }
            ],
        },
    )
    assert dataset_response.status_code == 200
    dataset_version_id = dataset_response.json()["current_version_id"]

    runner_image = "ghcr.io/example/claude-code-runner:latest"
    candidate_artifacts = tmp_path / "candidate-claude-artifacts"

    install_fake_k8s_runtime(
        monkeypatch,
        outputs={"alpha": "alpha", "beta": "not-beta"},
        artifact_contents={"alpha": "candidate alpha", "beta": "candidate beta"},
    )
    candidate_response = client.post(
        "/api/v1/experiments",
        json=_experiment_payload(
            name="candidate-claude-code",
            dataset_version_id=dataset_version_id,
            tags=["candidate", "claude-code-cli"],
            executor_backend="external-runner",
            executor_overrides={
                "runner_image": runner_image,
                "artifact_path": str(candidate_artifacts),
                "metadata": {
                    "runner_backend": "k8s-container",
                    "claude_code_cli": {
                        "command": "claude",
                        "args": ["--dangerously-skip-permissions"],
                        "version": "1.0.0",
                    },
                },
            },
        ),
    )
    assert candidate_response.status_code == 201
    candidate_experiment_id = candidate_response.json()["experiment_id"]
    assert client.post(f"/api/v1/experiments/{candidate_experiment_id}/start").status_code == 200
    assert _drain_background_work(worker_drain, limit=80, rounds=8) >= 1
    wait_until(
        lambda: (
            client.get(f"/api/v1/experiments/{candidate_experiment_id}/runs").json()[0]["judgement"]
            == "passed"
        ),
        timeout=5.0,
    )

    runs_response = client.get(f"/api/v1/experiments/{candidate_experiment_id}/runs")
    assert runs_response.status_code == 200
    runs = {item["dataset_sample_id"]: item for item in runs_response.json()}
    assert runs["sample-pass"]["judgement"] == "passed"
    assert runs["sample-pass"]["executor_backend"] == "external-runner"

    run_id = runs["sample-pass"]["run_id"]
    run_detail_response = client.get(f"/api/v1/runs/{run_id}")
    assert run_detail_response.status_code == 200
    run_detail = run_detail_response.json()
    assert run_detail["runner_backend"] == "k8s-container"
    assert run_detail["execution_backend"] == "kubernetes-job"
    assert run_detail["container_image"] == runner_image

    transcript_file = (
        candidate_artifacts
        / run_detail["run_id"]
        / run_detail["attempt_id"]
        / "artifacts"
        / "transcripts"
        / "claude-stream.jsonl"
    )
    assert transcript_file.read_text(encoding="utf-8").strip()

    export_response = client.post(
        "/api/v1/exports",
        json={
            "candidate_experiment_id": candidate_experiment_id,
            "judgements": ["passed"],
            "format": "jsonl",
        },
    )
    assert export_response.status_code == 200

    download_response = client.get(f"/api/v1/exports/{export_response.json()['export_id']}")
    assert download_response.status_code == 200
    rows = [json.loads(line) for line in download_response.text.splitlines()]
    assert len(rows) == 1
    assert rows[0]["dataset_sample_id"] == "sample-pass"
    assert rows[0]["executor_backend"] == "external-runner"
