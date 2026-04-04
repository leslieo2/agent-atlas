from __future__ import annotations

import json

import app.modules.agents.domain.starter_assets as starter_assets
from app.bootstrap.container import get_container
from app.modules.agents.domain.starter_assets import claude_code_starter_runtime_profile
from fastapi.testclient import TestClient
from tests.support.fake_docker import install_fake_docker_runtime


def _drain_background_work(worker_drain, *, limit: int, rounds: int = 6) -> int:
    processed_total = 0
    for _ in range(rounds):
        processed = worker_drain(limit=limit)
        processed_total += processed
        if processed == 0:
            break
    return processed_total


def test_live_starter_governed_loop_is_hermetic_and_export_ready(
    monkeypatch,
    worker_drain,
    wait_until,
) -> None:
    provisioning_commands: list[list[str]] = []
    image_ready = False

    def fake_docker_run(cmd, **kwargs):
        nonlocal image_ready
        provisioning_commands.append(list(cmd))
        if cmd[:3] == ["docker", "image", "inspect"]:
            return type(
                "Completed",
                (),
                {
                    "returncode": 0 if image_ready else 1,
                    "stderr": "" if image_ready else "missing",
                    "stdout": "",
                },
            )()
        if cmd[:2] == ["docker", "build"]:
            image_ready = True
            return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()
        raise AssertionError(f"Unexpected provisioning command: {cmd}")

    monkeypatch.setattr(starter_assets.subprocess, "run", fake_docker_run)
    get_container.cache_clear()
    install_fake_docker_runtime(monkeypatch, outputs={"alpha": "alpha"})

    from app.main import app

    with TestClient(app) as client:
        bootstrap_response = client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["agent_id"] == "claude-code-starter"
        assert provisioning_commands == [
            ["docker", "image", "inspect", starter_assets.CLAUDE_CODE_STARTER_RUNNER_IMAGE],
            [
                "docker",
                "build",
                "-f",
                str(
                    starter_assets._repo_root()
                    / "runtimes"
                    / "runner-base"
                    / "validation"
                    / "Dockerfile"
                ),
                "-t",
                starter_assets.CLAUDE_CODE_STARTER_RUNNER_IMAGE,
                ".",
            ],
        ]

        validation_response = client.post(
            "/api/v1/agents/claude-code-starter/validation-runs",
            json={
                "project": "atlas-validation",
                "dataset": "controlled-validation",
                "input_summary": "Validate the fresh live starter from governed state only",
                "prompt": "alpha",
                "tags": ["agents-surface", "governed-live-loop"],
                "project_metadata": {"validation_surface": "governed-live-loop"},
                "executor_config": claude_code_starter_runtime_profile().model_dump(mode="json"),
            },
        )
        assert validation_response.status_code == 200
        validation_run_id = validation_response.json()["run_id"]
        assert provisioning_commands[-1] == [
            "docker",
            "image",
            "inspect",
            starter_assets.CLAUDE_CODE_STARTER_RUNNER_IMAGE,
        ]

        assert _drain_background_work(worker_drain, limit=40) >= 1
        wait_until(
            lambda: (
                client.get("/api/v1/agents/published").json()[0]["latest_validation"]["status"]
                == "succeeded"
            )
        )

        published_response = client.get("/api/v1/agents/published")
        assert published_response.status_code == 200
        published = {item["agent_id"]: item for item in published_response.json()}
        starter = published["claude-code-starter"]
        assert starter["latest_validation"]["run_id"] == validation_run_id
        assert starter["validation_outcome"]["status"] == "passed"
        assert starter["validation_evidence"]["trace_url"] is not None
        assert starter["validation_evidence"]["trace_url"].startswith(
            "http://phoenix.test:6006/projects/"
        )

        dataset_response = client.post(
            "/api/v1/datasets",
            json={
                "name": "e2e-governed-live-loop",
                "description": "Hermetic live loop dataset created inside the backend e2e gate",
                "source": "playwright-hermetic",
                "version": "2026-04",
                "rows": [
                    {
                        "sample_id": "sample-1",
                        "input": "alpha",
                        "expected": "alpha",
                        "tags": ["support"],
                        "slice": "governed-live-loop",
                        "source": "playwright-hermetic",
                        "export_eligible": True,
                    }
                ],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = client.post(
            "/api/v1/experiments",
            json={
                "name": "e2e-governed-live-loop",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "tags": ["governed-live-loop"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200

        assert _drain_background_work(worker_drain, limit=40) >= 1
        wait_until(
            lambda: client.get(f"/api/v1/experiments/{experiment_id}").json()["status"]
            == "completed"
        )

        experiment_response = client.get(f"/api/v1/experiments/{experiment_id}")
        assert experiment_response.status_code == 200
        assert experiment_response.json()["status"] == "completed"

        runs_response = client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        run = runs[0]
        assert run["dataset_sample_id"] == "sample-1"
        assert run["judgement"] == "passed"
        assert run["executor_backend"] == "external-runner"
        assert run["trace_url"] is not None

        run_detail_response = client.get(f"/api/v1/runs/{run['run_id']}")
        assert run_detail_response.status_code == 200
        run_detail = run_detail_response.json()
        assert run_detail["runner_backend"] == "docker-container"
        assert run_detail["container_image"] == "atlas-claude-validation:local"
        assert run_detail["trace_pointer"]["trace_url"] == run["trace_url"]

        export_response = client.post(
            "/api/v1/exports",
            json={
                "candidate_experiment_id": experiment_id,
                "judgements": ["passed"],
                "format": "jsonl",
            },
        )
        assert export_response.status_code == 200
        export_payload = export_response.json()
        assert export_payload["row_count"] == 1

        history_response = client.get("/api/v1/exports")
        assert history_response.status_code == 200
        assert any(
            item["export_id"] == export_payload["export_id"] for item in history_response.json()
        )

        download_response = client.get(f"/api/v1/exports/{export_payload['export_id']}")
        assert download_response.status_code == 200
        rows = [json.loads(line) for line in download_response.text.splitlines()]
        assert len(rows) == 1
        assert rows[0]["dataset_sample_id"] == "sample-1"
        assert rows[0]["trace_url"] == run["trace_url"]
        assert rows[0]["executor_backend"] == "external-runner"
        assert rows[0]["published_agent_snapshot"]["manifest"]["agent_id"] == "claude-code-starter"
