from __future__ import annotations

import textwrap

from app.bootstrap.container import get_container
from app.core.config import RuntimeMode
from app.core.errors import ProviderAuthError
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult
from pydantic import SecretStr


def test_end_to_end_workbench_flow(monkeypatch, client, worker_drain):
    container = get_container()
    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        lambda *_args, **_kwargs: PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="mocked e2e output",
                latency_ms=1,
                token_usage=2,
                provider="mock",
                resolved_model="gpt-5.4-mini",
            )
        ),
    )

    dataset = client.post(
        "/api/v1/datasets",
        json={"name": "e2e-ds", "rows": [{"sample_id": "s-1", "input": "Hello dataset"}]},
    )
    assert dataset.status_code == 200
    assert dataset.json()["name"] == "e2e-ds"

    run = client.post(
        "/api/v1/runs",
        json={
            "project": "e2e-project",
            "dataset": "e2e-ds",
            "agent_id": "basic",
            "input_summary": "e2e smoke run",
            "prompt": "Generate safe output.",
            "tags": ["e2e"],
        },
    )
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.json()["status"] == "succeeded"

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    trajectory_rows = trajectory.json()
    assert len(trajectory_rows) >= 1

    artifact = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [run_id], "format": "jsonl"},
    )
    assert artifact.status_code == 200
    artifact_id = artifact.json()["artifact_id"]
    assert artifact_id

    artifact_file = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_file.status_code == 200
    assert artifact_file.headers["content-type"].startswith("application/")


def test_end_to_end_eval_flow_supports_failure_triage_and_export(monkeypatch, client, worker_drain):
    container = get_container()

    def execute_published(_run_id, payload):
        if payload.prompt == "runtime":
            raise ProviderAuthError("provider authentication failed")

        output = {
            "alpha": "alpha",
            "beta": "not-beta",
        }.get(payload.prompt, payload.prompt)

        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output=output,
                latency_ms=1,
                token_usage=2,
                provider="mock",
                resolved_model="gpt-5.4-mini",
            )
        )

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    dataset = client.post(
        "/api/v1/datasets",
        json={
            "name": "eval-e2e-ds",
            "rows": [
                {"sample_id": "sample-pass", "input": "alpha", "expected": "alpha"},
                {"sample_id": "sample-fail", "input": "beta", "expected": "beta"},
                {"sample_id": "sample-runtime", "input": "runtime", "expected": "runtime"},
            ],
        },
    )
    assert dataset.status_code == 200

    created = client.post(
        "/api/v1/eval-jobs",
        json={
            "agent_id": "basic",
            "dataset": "eval-e2e-ds",
            "project": "eval-e2e-project",
            "tags": ["e2e"],
            "scoring_mode": "exact_match",
        },
    )
    assert created.status_code == 201
    eval_job_id = created.json()["eval_job_id"]

    assert worker_drain(limit=20) >= 1

    detail = client.get(f"/api/v1/eval-jobs/{eval_job_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["passed_count"] == 1
    assert detail.json()["failed_count"] == 1
    assert detail.json()["runtime_error_count"] == 1
    assert detail.json()["failure_distribution"] == {"mismatch": 1, "provider_call": 1}

    samples = client.get(f"/api/v1/eval-jobs/{eval_job_id}/samples")
    assert samples.status_code == 200
    sample_map = {row["dataset_sample_id"]: row for row in samples.json()}
    failed_run_id = sample_map["sample-fail"]["run_id"]
    assert failed_run_id

    trajectory = client.get(f"/api/v1/runs/{failed_run_id}/trajectory")
    assert trajectory.status_code == 200
    assert len(trajectory.json()) >= 1

    artifact = client.post(
        "/api/v1/artifacts/export",
        json={"run_ids": [failed_run_id], "format": "jsonl"},
    )
    assert artifact.status_code == 200
    artifact_id = artifact.json()["artifact_id"]
    assert artifact_id

    artifact_file = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert artifact_file.status_code == 200
    assert artifact_file.headers["content-type"].startswith("application/")


def test_end_to_end_langchain_agent_can_be_discovered_published_and_run(
    monkeypatch,
    client,
    worker_drain,
    tmp_path,
):
    package_name = "test_agent_plugins_langchain"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "graph_bot.py").write_text(
        textwrap.dedent(
            """
            AGENT_MANIFEST = {
                "agent_id": "graph-bot",
                "name": "Graph Bot",
                "description": "LangGraph-backed test agent.",
                "framework": "langchain",
                "default_model": "gpt-5.4-mini",
                "tags": ["langchain", "test"],
            }


            class RunnableGraph:
                def invoke(self, payload):
                    return {
                        "output": f"graph:{payload['input']}",
                        "usage": {"total_tokens": 7},
                    }


            def build_agent(context):
                return RunnableGraph()
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    container = get_container()
    monkeypatch.setattr(container.infrastructure.agent_source_catalog, "package_name", package_name)
    monkeypatch.setattr(container.infrastructure.model_runtime, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(container.infrastructure.model_runtime, "api_key", SecretStr("sk-test"))

    discovered = client.get("/api/v1/agents/discovered")
    assert discovered.status_code == 200
    discovered_by_id = {agent["agent_id"]: agent for agent in discovered.json()}
    assert discovered_by_id["graph-bot"]["framework"] == "langchain"
    assert discovered_by_id["graph-bot"]["validation_status"] == "valid"

    publish = client.post("/api/v1/agents/graph-bot/publish")
    assert publish.status_code == 200
    assert publish.json()["framework"] == "langchain"

    run = client.post(
        "/api/v1/runs",
        json={
            "project": "langchain-project",
            "dataset": "e2e-ds",
            "agent_id": "graph-bot",
            "input_summary": "langchain smoke run",
            "prompt": "Generate graph output.",
            "tags": ["e2e", "langchain"],
        },
    )
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json()["status"] == "succeeded"
    assert run_state.json()["agent_type"] == "langchain"
    assert run_state.json()["execution_backend"] == "langgraph"
    assert run_state.json()["provenance"]["framework"] == "langchain"

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    assert len(trajectory.json()) == 1
    assert trajectory.json()[0]["step_type"] == "llm"
