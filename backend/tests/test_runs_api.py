from __future__ import annotations

from datetime import UTC, datetime
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
        "agent_id": "basic",
        "input_summary": "health check smoke",
        "prompt": "Summarize all current runs.",
        "tags": ["smoke", "api"],
        "project_metadata": {"team": "backend"},
    }

    created = client.post("/api/v1/runs", json=payload)
    assert created.status_code == 201
    run_id = created.json()["run_id"]

    got = client.get(f"/api/v1/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["run_id"] == run_id
    assert got.json()["agent_id"] == "basic"
    assert got.json()["status"] == RunStatus.QUEUED.value
    snapshot = got.json()["provenance"]["published_agent_snapshot"]
    assert snapshot["manifest"] == {
        "agent_id": "basic",
        "name": "Basic",
        "description": "Minimal plugin agent for smoke testing the SDK execution path.",
        "framework": "openai-agents-sdk",
        "default_model": "gpt-5.4-mini",
        "tags": ["example", "smoke"],
    }
    assert snapshot["entrypoint"] == "app.agent_plugins.basic:build_agent"
    assert (
        snapshot["published_at"]
        == got.json()["provenance"]["published_agent_snapshot"]["published_at"]
    )
    assert snapshot["runtime_artifact"]["build_status"] == "ready"
    assert snapshot["runtime_artifact"]["artifact_ref"].startswith("source://basic@")


def test_create_run_without_dataset(client):
    payload = {
        "project": "smoke-test",
        "agent_id": "basic",
        "input_summary": "prompt only smoke",
        "prompt": "Summarize all current runs.",
    }

    created = client.post("/api/v1/runs", json=payload)
    assert created.status_code == 201
    assert created.json()["dataset"] is None


def test_run_stays_queued_until_worker_runs(client):
    payload = {
        "project": "queued-test",
        "dataset": "smoke-ds",
        "agent_id": "customer_service",
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
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type="openai-agents-sdk",
        status=RunStatus.RUNNING,
    )
    container.infrastructure.run_repository.save(run)

    terminated = client.post(f"/api/v1/runs/{run.run_id}/terminate")
    assert terminated.status_code == 200
    assert terminated.json()["terminated"] is True

    already_terminated = client.post(f"/api/v1/runs/{run.run_id}/terminate")
    assert already_terminated.status_code == 400


def test_create_run_with_unknown_agent_returns_structured_400(client):
    response = client.post(
        "/api/v1/runs",
        json={
            "project": "smoke-test",
            "agent_id": "unknown-agent",
            "input_summary": "bad agent",
            "prompt": "Do not run.",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "agent_not_published",
            "message": "agent_id 'unknown-agent' is not published",
            "agent_id": "unknown-agent",
        }
    }


def test_list_runs_accepts_naive_and_offset_datetime_filters(client):
    container = get_container()
    earlier_run = RunRecord(
        run_id=uuid4(),
        input_summary="older run",
        project="timezone-project",
        dataset="timezone-ds",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type="openai-agents-sdk",
        created_at=datetime(2026, 3, 25, 9, 0, tzinfo=UTC),
    )
    later_run = RunRecord(
        run_id=uuid4(),
        input_summary="later run",
        project="timezone-project",
        dataset="timezone-ds",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type="openai-agents-sdk",
        created_at=datetime(2026, 3, 25, 11, 0, tzinfo=UTC),
    )
    container.infrastructure.run_repository.save(earlier_run)
    container.infrastructure.run_repository.save(later_run)

    naive_response = client.get(
        "/api/v1/runs",
        params={"project": "timezone-project", "created_from": "2026-03-25T10:00:00"},
    )
    assert naive_response.status_code == 200
    assert [run["run_id"] for run in naive_response.json()] == [str(later_run.run_id)]

    offset_response = client.get(
        "/api/v1/runs",
        params={"project": "timezone-project", "created_to": "2026-03-25T18:30:00+08:00"},
    )
    assert offset_response.status_code == 200
    assert [run["run_id"] for run in offset_response.json()] == [str(earlier_run.run_id)]
