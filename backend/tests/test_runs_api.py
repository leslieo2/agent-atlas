from __future__ import annotations

from uuid import uuid4

from app.bootstrap.container import get_container
from app.core.config import RuntimeMode, settings
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.enums import RunStatus
from fastapi.testclient import TestClient


def test_run_list_and_filters_include_seeded_data(client):
    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    all_runs = response.json()
    assert any(run["project"] == "sales-assistant" for run in all_runs)

    response = client.get("/api/v1/runs", params={"status": RunStatus.SUCCEEDED.value})
    assert response.status_code == 200
    assert all(run["status"] == RunStatus.SUCCEEDED.value for run in response.json())


def test_live_mode_does_not_seed_demo_by_default(monkeypatch):
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "seed_demo", None)

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_seed_demo_can_be_explicitly_enabled_in_live_mode(monkeypatch):
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "seed_demo", True)

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/runs")

    assert response.status_code == 200
    assert any(run["project"] == "sales-assistant" for run in response.json())


def test_create_run_and_get_by_id(client):
    payload = {
        "project": "smoke-test",
        "dataset": "smoke-ds",
        "model": "gpt-4.1-mini",
        "agent_type": "openai-agents-sdk",
        "input_summary": "health check smoke",
        "prompt": "Summarize all current runs.",
        "tags": ["smoke", "api"],
        "tool_config": {"primary_tool": "vector_search"},
        "project_metadata": {"team": "backend"},
    }

    created = client.post("/api/v1/runs", json=payload)
    assert created.status_code == 201
    run_id = created.json()["run_id"]

    got = client.get(f"/api/v1/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["run_id"] == run_id
    assert got.json()["status"] == RunStatus.QUEUED.value


def test_run_stays_queued_until_worker_runs(client):
    payload = {
        "project": "queued-test",
        "dataset": "smoke-ds",
        "model": "gpt-4.1-mini",
        "agent_type": "openai-agents-sdk",
        "input_summary": "queue only",
        "prompt": "Do not run yet.",
    }

    created = client.post("/api/v1/runs", json=payload)
    assert created.status_code == 201
    run_id = created.json()["run_id"]

    got = client.get(f"/api/v1/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["status"] == RunStatus.QUEUED.value


def test_terminate_running_run_in_memory(client):
    container = get_container()
    run = RunRecord(
        run_id=uuid4(),
        input_summary="temporary run",
        project="tmp-project",
        dataset="tmp-ds",
        model="gpt-4.1-mini",
        agent_type="openai-agents-sdk",
        status=RunStatus.RUNNING,
    )
    container.run_repository.save(run)

    terminated = client.post(f"/api/v1/runs/{run.run_id}/terminate")
    assert terminated.status_code == 200
    assert terminated.json()["terminated"] is True

    already_terminated = client.post(f"/api/v1/runs/{run.run_id}/terminate")
    assert already_terminated.status_code == 400
