from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import app.modules.agents.domain.starter_assets as starter_assets
import pytest
from app.agent_tracing.exporters.otlp import OtlpTraceExporter
from app.bootstrap.container import get_container
from app.bootstrap.wiring import infrastructure as infrastructure_wiring
from app.core.config import settings
from app.core.errors import ProviderAuthError
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RuntimeExecutionResult,
)
from app.modules.shared.domain.models import TracePointer
from tests.fixtures.agents import build_fixture_published_agent
from tests.support.fake_docker import install_fake_docker_runtime


@pytest.fixture(autouse=True)
def _stub_starter_carrier_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(starter_assets, "provision_claude_code_starter_carrier", lambda: None)


@pytest.fixture(autouse=True)
def _seed_basic_published_agent() -> None:
    get_container().infrastructure.published_agent_repository.save_agent(
        build_fixture_published_agent("basic")
    )


def _drain_background_work(worker_drain, *, limit: int, rounds: int = 6) -> int:
    processed_total = 0
    for _ in range(rounds):
        processed = worker_drain(limit=limit)
        processed_total += processed
        if processed == 0:
            break
    return processed_total


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
    executor_backend: str = "k8s-job",
    runner_mode: str | None = None,
    executor_overrides: dict[str, object] | None = None,
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
    if executor_overrides:
        executor_config.update(executor_overrides)

    return {
        "name": name,
        "spec": {
            "dataset_version_id": dataset_version_id,
            "published_agent_id": "basic",
            "model_settings": {
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
    wait_until,
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
            executor_backend="local-runner",
            runner_mode="in-process",
        ),
    )
    assert baseline_response.status_code == 201
    baseline_experiment_id = baseline_response.json()["experiment_id"]
    start_baseline = client.post(f"/api/v1/experiments/{baseline_experiment_id}/start")
    assert start_baseline.status_code == 200
    assert _drain_background_work(worker_drain, limit=40) >= 1
    wait_until(
        lambda: client.get(f"/api/v1/experiments/{baseline_experiment_id}").json()["status"]
        == "completed"
    )

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
    start_candidate = client.post(f"/api/v1/experiments/{candidate_experiment_id}/start")
    assert start_candidate.status_code == 200
    assert _drain_background_work(worker_drain, limit=40) >= 1
    wait_until(
        lambda: client.get(f"/api/v1/experiments/{candidate_experiment_id}").json()["status"]
        == "completed"
    )
    assert _drain_background_work(worker_drain, limit=40) >= 0

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
    wait_until(
        lambda: (
            client.get(
                "/api/v1/experiments/compare",
                params={
                    "baseline_experiment_id": baseline_experiment_id,
                    "candidate_experiment_id": candidate_experiment_id,
                },
            )
            .json()["distribution"]
            .get("regressed")
            == 1
        )
    )
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


def test_experiments_api_accepts_archived_valid_published_snapshot_for_new_runs(client) -> None:
    container = get_container()
    published_agent = build_fixture_published_agent("basic")
    container.infrastructure.published_agent_repository.save_agent(published_agent)

    archived = published_agent.model_copy(
        update={
            "manifest": published_agent.manifest.model_copy(update={"agent_id": "archived-basic"}),
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(archived)

    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "archived-agent-dataset",
            "description": "Dataset for archived snapshot rejection",
            "source": "crm",
            "version": "2026-03",
            "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
        },
    )
    assert dataset_response.status_code == 200
    dataset_version_id = dataset_response.json()["current_version_id"]

    response = client.post(
        "/api/v1/experiments",
        json={
            "name": "archived-snapshot",
            "spec": {
                "dataset_version_id": dataset_version_id,
                "published_agent_id": "archived-basic",
                "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                "prompt_config": {"prompt_version": "2026-03"},
                "toolset_config": {"tools": [], "metadata": {}},
                "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                "executor_config": {
                    "backend": "local-runner",
                    "timeout_seconds": 600,
                    "max_steps": 32,
                    "concurrency": 1,
                    "resources": {},
                    "tracing_backend": "phoenix",
                    "artifact_path": None,
                    "metadata": {"runner_mode": "in-process"},
                },
                "tags": [],
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["spec"]["published_agent_id"] == "archived-basic"


def test_experiments_api_live_mode_starts_with_bootstrapped_starter_agent(
    monkeypatch,
    worker_drain,
) -> None:
    get_container.cache_clear()

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["agent_id"] == "claude-code-starter"

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-starter-dataset",
                "description": "Dataset for fresh live starter experiment path",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-starter-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "executor_config": {
                        "backend": "external-runner",
                        "runner_image": "atlas-claude-validation:local",
                        "metadata": {"runner_backend": "k8s-container"},
                    },
                    "tags": ["live-starter"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200

        assert worker_drain(limit=10) >= 1

        experiment_detail = live_client.get(f"/api/v1/experiments/{experiment_id}")
        assert experiment_detail.status_code == 200
        detail = experiment_detail.json()
        assert detail["status"] == "completed"
        assert detail["completed_count"] == 1
        assert detail["failed_count"] == 0

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        run_detail = live_client.get(f"/api/v1/runs/{runs[0]['run_id']}")
        assert run_detail.status_code == 200
        assert run_detail.json()["agent_id"] == "claude-code-starter"


def test_experiments_api_live_mode_runs_with_state_backed_formal_agent(
    monkeypatch,
    worker_drain,
) -> None:
    get_container.cache_clear()

    container = get_container()
    container.infrastructure.published_agent_repository.save_agent(
        build_fixture_published_agent("basic")
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-formal-agent-dataset",
                "description": "Dataset for state-backed formal agent experiment path",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-formal-agent-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "basic",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "executor_config": {
                        "backend": "external-runner",
                        "runner_image": "atlas-claude-validation:local",
                        "metadata": {"runner_backend": "k8s-container"},
                    },
                    "tags": ["live-formal-agent"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200

        assert worker_drain(limit=10) >= 1

        experiment_detail = live_client.get(f"/api/v1/experiments/{experiment_id}")
        assert experiment_detail.status_code == 200
        detail = experiment_detail.json()
        assert detail["status"] == "completed"
        assert detail["completed_count"] == 1
        assert detail["failed_count"] == 0

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        run_detail = live_client.get(f"/api/v1/runs/{runs[0]['run_id']}")
        assert run_detail.status_code == 200
        assert run_detail.json()["agent_id"] == "basic"


def test_experiments_api_live_mode_pins_published_snapshot_across_unpublish(
    monkeypatch,
    worker_drain,
    wait_until,
) -> None:
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-pinned-agent-dataset",
                "description": "Dataset for pinned live agent handoff",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-pinned-agent-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "executor_config": {
                        "backend": "external-runner",
                        "runner_image": "atlas-claude-validation:local",
                        "metadata": {"runner_backend": "docker-container"},
                    },
                    "tags": ["live-starter"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        unpublish_response = live_client.post("/api/v1/agents/claude-code-starter/unpublish")
        assert unpublish_response.status_code == 200

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200
        assert _drain_background_work(worker_drain, limit=40) >= 1
        wait_until(
            lambda: live_client.get(f"/api/v1/experiments/{experiment_id}").json()["status"]
            == "completed"
        )

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        assert runs[0]["published_agent_snapshot"]["manifest"]["agent_id"] == "claude-code-starter"


def test_experiments_api_live_mode_rejects_corrupt_published_rows_for_new_experiments(
    monkeypatch,
) -> None:
    get_container.cache_clear()

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        container = get_container()
        base_agent = build_fixture_published_agent("basic")
        corrupt = base_agent.model_copy(
            update={
                "manifest": base_agent.manifest.model_copy(update={"agent_id": "corrupt-basic"}),
                "source_fingerprint": "",
                "execution_reference": {"artifact_ref": None, "image_ref": None},
            },
            deep=True,
        )
        container.infrastructure.published_agent_repository.save_agent(corrupt)

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-corrupt-agent-dataset",
                "description": "Dataset for corrupt live agent governance",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "corrupt-live-agent",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "corrupt-basic",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "executor_config": {
                        "backend": "external-runner",
                        "runner_image": "atlas-claude-validation:local",
                        "metadata": {"runner_backend": "docker-container"},
                    },
                    "tags": [],
                },
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == {
            "code": "agent_not_published",
            "message": "agent_id 'corrupt-basic' is not published",
            "agent_id": "corrupt-basic",
        }


def test_experiments_api_live_mode_bootstrapped_starter_uses_default_runtime_profile(
    monkeypatch,
    worker_drain,
) -> None:
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["default_runtime_profile"]["backend"] == "external-runner"
        assert "binding" not in bootstrap_response.json()["default_runtime_profile"]

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-starter-default-runtime-dataset",
                "description": "Dataset for first live experiment default path",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-starter-default-runtime-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "tags": ["live-starter", "default-runtime"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200

        assert _drain_background_work(worker_drain, limit=40) >= 1

        experiment_detail = live_client.get(f"/api/v1/experiments/{experiment_id}")
        assert experiment_detail.status_code == 200
        detail = experiment_detail.json()
        assert detail["status"] == "completed"
        assert detail["completed_count"] == 1
        assert detail["failed_count"] == 0

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        assert runs[0]["dataset_sample_id"] == "sample-1"
        assert runs[0]["judgement"] == "passed"

        run_detail = live_client.get(f"/api/v1/runs/{runs[0]['run_id']}")
        assert run_detail.status_code == 200
        assert run_detail.json()["runner_backend"] == "docker-container"
        assert run_detail.json()["container_image"] == "atlas-claude-validation:local"
        assert run_detail.json()["trace_pointer"]["trace_url"] is not None


def test_experiments_api_live_mode_rejects_corrupt_published_agent_rows(
    monkeypatch,
) -> None:
    get_container.cache_clear()

    container = get_container()
    published_agent = build_fixture_published_agent("basic")
    container.infrastructure.published_agent_repository.save_agent(published_agent)
    assert published_agent is not None
    corrupted = published_agent.model_copy(
        update={
            "manifest": published_agent.manifest.model_copy(update={"agent_id": "corrupt-basic"}),
            "source_fingerprint": "",
            "execution_reference": {"artifact_ref": None, "image_ref": None},
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(corrupted)

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "corrupt-live-formal-dataset",
                "description": "Dataset for corrupt published agent rejection in live mode",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "corrupt-live-formal-agent",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "corrupt-basic",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "executor_config": {
                        "backend": "external-runner",
                        "runner_image": "atlas-claude-validation:local",
                        "metadata": {"runner_backend": "k8s-container"},
                    },
                    "tags": ["live-formal-agent", "corrupt"],
                },
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == {
            "code": "agent_not_published",
            "message": "agent_id 'corrupt-basic' is not published",
            "agent_id": "corrupt-basic",
        }


def test_experiments_api_live_mode_starter_emits_trace_deeplink_without_explicit_otlp_endpoint(
    monkeypatch,
    worker_drain,
) -> None:
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", None)
    monkeypatch.setattr(settings, "phoenix_base_url", "http://phoenix.test:6006")
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-starter-phoenix-deeplink-dataset",
                "description": "Dataset for derived Phoenix OTLP endpoint path",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-starter-phoenix-deeplink-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "tags": ["live-starter", "phoenix-deeplink"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200

        assert _drain_background_work(worker_drain, limit=40) >= 1

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) == 1
        assert runs[0]["trace_url"] is not None
        assert runs[0]["trace_url"].startswith("http://phoenix.test:6006/projects/")

        run_detail = live_client.get(f"/api/v1/runs/{runs[0]['run_id']}")
        assert run_detail.status_code == 200
        assert run_detail.json()["trace_pointer"]["trace_url"] == runs[0]["trace_url"]


def test_experiments_api_live_mode_starter_completes_with_non_null_trace_url_when_otlp_returns_bad_gateway(  # noqa: E501
    monkeypatch,
    worker_drain,
) -> None:
    class _BadGatewayHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            content_length = int(self.headers.get("content-length", "0"))
            if content_length:
                self.rfile.read(content_length)
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"bad gateway")

        def log_message(self, format, *args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), _BadGatewayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    monkeypatch.setattr(settings, "phoenix_base_url", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", f"http://127.0.0.1:{port}/v1/traces")
    monkeypatch.setattr(settings, "tracing_otlp_timeout_seconds", 1.0)
    monkeypatch.setattr(infrastructure_wiring, "OtlpTraceExporter", OtlpTraceExporter)
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    try:
        with TestClient(app) as live_client:
            bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
            assert bootstrap_response.status_code == 200

            dataset_response = live_client.post(
                "/api/v1/datasets",
                json={
                    "name": "live-starter-phoenix-bad-gateway-dataset",
                    "description": "Dataset for failing OTLP export path",
                    "source": "crm",
                    "version": "2026-04",
                    "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
                },
            )
            assert dataset_response.status_code == 200
            dataset_version_id = dataset_response.json()["current_version_id"]

            create_response = live_client.post(
                "/api/v1/experiments",
                json={
                    "name": "live-starter-phoenix-bad-gateway-experiment",
                    "spec": {
                        "dataset_version_id": dataset_version_id,
                        "published_agent_id": "claude-code-starter",
                        "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                        "prompt_config": {"prompt_version": "2026-04"},
                        "toolset_config": {"tools": [], "metadata": {}},
                        "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                        "tags": ["live-starter", "phoenix-bad-gateway"],
                    },
                },
            )
            assert create_response.status_code == 201
            experiment_id = create_response.json()["experiment_id"]

            start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
            assert start_response.status_code == 200

            assert _drain_background_work(worker_drain, limit=40) >= 1

            experiment_response = live_client.get(f"/api/v1/experiments/{experiment_id}")
            assert experiment_response.status_code == 200
            assert experiment_response.json()["status"] == "completed"

            runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
            assert runs_response.status_code == 200
            runs = runs_response.json()
            assert len(runs) == 1
            assert runs[0]["run_status"] == "succeeded"
            assert runs[0]["trace_url"] is not None
            assert runs[0]["trace_url"].startswith(f"http://127.0.0.1:{port}")
    finally:
        server.shutdown()
        server.server_close()


def test_experiments_api_run_list_falls_back_to_run_trace_pointer_when_evaluation_trace_is_null(
    monkeypatch,
    worker_drain,
) -> None:
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "not-alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-starter-trace-fallback-dataset",
                "description": "Dataset for experiments trace-url fallback",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-starter-trace-fallback-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "tags": ["live-starter", "trace-fallback"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200
        assert _drain_background_work(worker_drain, limit=40) >= 1

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        run_id = runs_response.json()[0]["run_id"]

        container = get_container()
        evaluations = container.infrastructure.run_evaluation_repository.list_for_experiment(
            experiment_id
        )
        evaluation = next((record for record in evaluations if str(record.run_id) == run_id), None)
        assert evaluation is not None
        assert evaluation.trace_url is not None
        container.infrastructure.run_evaluation_repository.save(
            evaluation.model_copy(update={"trace_url": None})
        )

        refreshed_runs = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert refreshed_runs.status_code == 200
        refreshed_row = refreshed_runs.json()[0]
        assert refreshed_row["trace_url"] is not None

        run_detail = live_client.get(f"/api/v1/runs/{run_id}")
        assert run_detail.status_code == 200
        assert refreshed_row["trace_url"] == run_detail.json()["trace_pointer"]["trace_url"]


def test_experiments_api_run_list_falls_back_to_project_url_when_trace_url_is_missing(
    monkeypatch,
    worker_drain,
) -> None:
    get_container.cache_clear()
    install_fake_docker_runtime(
        monkeypatch,
        outputs={"alpha": "alpha"},
    )

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        dataset_response = live_client.post(
            "/api/v1/datasets",
            json={
                "name": "live-starter-project-url-fallback-dataset",
                "description": "Dataset for experiments project-url fallback",
                "source": "crm",
                "version": "2026-04",
                "rows": [{"sample_id": "sample-1", "input": "alpha", "expected": "alpha"}],
            },
        )
        assert dataset_response.status_code == 200
        dataset_version_id = dataset_response.json()["current_version_id"]

        create_response = live_client.post(
            "/api/v1/experiments",
            json={
                "name": "live-starter-project-url-fallback-experiment",
                "spec": {
                    "dataset_version_id": dataset_version_id,
                    "published_agent_id": "claude-code-starter",
                    "model_settings": {"model": "gpt-5.4-mini", "temperature": 0},
                    "prompt_config": {"prompt_version": "2026-04"},
                    "toolset_config": {"tools": [], "metadata": {}},
                    "evaluator_config": {"scoring_mode": "exact_match", "metadata": {}},
                    "tags": ["live-starter", "project-url-fallback"],
                },
            },
        )
        assert create_response.status_code == 201
        experiment_id = create_response.json()["experiment_id"]

        start_response = live_client.post(f"/api/v1/experiments/{experiment_id}/start")
        assert start_response.status_code == 200
        assert _drain_background_work(worker_drain, limit=40) >= 1

        runs_response = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert runs_response.status_code == 200
        run_id = runs_response.json()[0]["run_id"]

        container = get_container()
        evaluations = container.infrastructure.run_evaluation_repository.list_for_experiment(
            experiment_id
        )
        evaluation = next((record for record in evaluations if str(record.run_id) == run_id), None)
        assert evaluation is not None
        container.infrastructure.run_evaluation_repository.save(
            evaluation.model_copy(update={"trace_url": None})
        )

        run_record = container.infrastructure.run_repository.get(run_id)
        assert run_record is not None
        assert run_record.trace_pointer is not None
        assert run_record.trace_pointer.project_url is not None
        container.infrastructure.run_repository.save(
            run_record.model_copy(
                update={
                    "trace_pointer": TracePointer(
                        backend=run_record.trace_pointer.backend,
                        trace_id=run_record.trace_pointer.trace_id,
                        trace_url=None,
                        project_url=run_record.trace_pointer.project_url,
                    )
                }
            )
        )

        refreshed_runs = live_client.get(f"/api/v1/experiments/{experiment_id}/runs")
        assert refreshed_runs.status_code == 200
        refreshed_row = refreshed_runs.json()[0]
        assert refreshed_row["trace_url"] == run_record.trace_pointer.project_url
