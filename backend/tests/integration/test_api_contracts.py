from __future__ import annotations

from uuid import uuid4

from app.bootstrap.container import get_container
from app.modules.agents.domain.models import (
    AgentManifest,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
)
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.enums import RunStatus


def test_runs_api_create_list_and_trajectory_filters(monkeypatch, client, worker_drain):
    container = get_container()
    monkeypatch.setattr(
        container.model_runtime,
        "execute_published",
        lambda *_args, **_kwargs: RuntimeExecutionResult(
            output="mocked integration output",
            latency_ms=1,
            token_usage=1,
            provider="mock",
            resolved_model="gpt-4.1-mini",
        ),
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration",
            "dataset": "crm-v2",
            "agent_id": "basic",
            "input_summary": "integration smoke",
            "prompt": "Say hello.",
            "tags": ["integration"],
        },
    )
    assert response.status_code == 201

    run = response.json()
    run_id = run["run_id"]
    assert run["project"] == "integration"
    assert run["agent_id"] == "basic"
    assert run["status"] == RunStatus.QUEUED.value

    assert worker_drain() >= 1

    current = client.get(f"/api/v1/runs/{run_id}")
    assert current.status_code == 200
    data = current.json()
    assert data["status"] == RunStatus.SUCCEEDED.value

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory").json()
    assert isinstance(trajectory, list)
    assert len(trajectory) >= 1
    assert all(step["step_type"] == "llm" for step in trajectory)

    filtered = client.get("/api/v1/runs", params={"project": "integration"}).json()
    assert any(item["run_id"] == run_id for item in filtered)

    filtered_by_agent = client.get("/api/v1/runs", params={"agent_id": "basic"}).json()
    assert any(item["run_id"] == run_id for item in filtered_by_agent)


def test_trace_ingest_and_normalize_endpoints(client):
    run_id = str(uuid4())

    normalize_payload = {
        "run_id": run_id,
        "span_id": "span-normalize",
        "parent_span_id": None,
        "step_type": "tool",
        "name": "normalize-step",
        "input": {"task": "normalize"},
        "output": {"ok": True},
        "tool_name": "mcp",
        "latency_ms": 7,
        "token_usage": 3,
        "image_digest": "sha256:normalize",
        "prompt_version": "v1",
    }

    normalized = client.post("/api/v1/traces/normalize", json=normalize_payload)
    assert normalized.status_code == 200
    normalized_payload = normalized.json()
    assert normalized_payload["run_id"] == run_id
    assert normalized_payload["step_type"] == "tool"

    ingested = client.post("/api/v1/traces/ingest", json=normalize_payload)
    assert ingested.status_code == 201
    assert ingested.json()["status"] == "ok"
    assert ingested.json()["span_id"] == "span-normalize"

    traces = client.get(f"/api/v1/runs/{run_id}/traces").json()
    assert len(traces) == 1
    assert traces[0]["span_id"] == "span-normalize"

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory").json()
    assert len(trajectory) == 1
    assert trajectory[0]["id"] == "span-normalize"
    assert trajectory[0]["step_type"] == "tool"
    assert trajectory[0]["tool_name"] == "mcp"


def test_agents_list_available_published_agents(client):
    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    assert {agent["agent_id"] for agent in response.json()} == {
        "basic",
        "customer_service",
        "tools",
    }


def test_agents_discovered_publish_and_unpublish_flow(client):
    container = get_container()
    assert container.agent_publication_commands.unpublish("tools") is True

    discovered = client.get("/api/v1/agents/discovered")
    assert discovered.status_code == 200
    by_id = {agent["agent_id"]: agent for agent in discovered.json()}
    assert by_id["tools"]["publish_state"] == "draft"
    assert by_id["tools"]["validation_status"] == "valid"

    publish = client.post("/api/v1/agents/tools/publish")
    assert publish.status_code == 200
    assert publish.json()["agent_id"] == "tools"
    assert publish.json()["entrypoint"] == "app.agent_plugins.tools:build_agent"

    runnable_after_publish = client.get("/api/v1/agents")
    assert runnable_after_publish.status_code == 200
    assert "tools" in {agent["agent_id"] for agent in runnable_after_publish.json()}

    unpublish = client.post("/api/v1/agents/tools/unpublish")
    assert unpublish.status_code == 200
    assert unpublish.json() == {"agent_id": "tools", "published": False}

    runnable_after_unpublish = client.get("/api/v1/agents")
    assert runnable_after_unpublish.status_code == 200
    assert "tools" not in {agent["agent_id"] for agent in runnable_after_unpublish.json()}


def test_runs_reject_unpublished_agent(client):
    container = get_container()
    assert container.agent_publication_commands.unpublish("basic") is True

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration",
            "agent_id": "basic",
            "input_summary": "should fail",
            "prompt": "Do not run.",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "agent_not_published",
            "message": "agent_id 'basic' is not published",
            "agent_id": "basic",
        }
    }


def test_published_invalid_agent_disappears_from_runnable_catalog(monkeypatch, client):
    container = get_container()

    monkeypatch.setattr(
        container.agent_discovery,
        "list_agents",
        lambda: [
            DiscoveredAgent(
                manifest=AgentManifest(
                    agent_id="basic",
                    name="Basic",
                    description="Broken plugin",
                    default_model="gpt-4.1-mini",
                    tags=["example", "smoke"],
                ),
                entrypoint="app.agent_plugins.basic:build_agent",
                validation_status=AgentValidationStatus.INVALID,
                validation_issues=[
                    AgentValidationIssue(
                        code="build_agent_failed",
                        message="entrypoint validation failed",
                    )
                ],
            )
        ],
    )

    runnable = client.get("/api/v1/agents")
    assert runnable.status_code == 200
    assert runnable.json() == []

    discovered = client.get("/api/v1/agents/discovered")
    assert discovered.status_code == 200
    assert discovered.json() == [
        {
            "agent_id": "basic",
            "name": "Basic",
            "description": "Broken plugin",
            "framework": "openai-agents-sdk",
            "entrypoint": "app.agent_plugins.basic:build_agent",
            "default_model": "gpt-4.1-mini",
            "tags": ["example", "smoke"],
            "publish_state": "published",
            "validation_status": "invalid",
            "validation_issues": [
                {
                    "code": "build_agent_failed",
                    "message": "entrypoint validation failed",
                }
            ],
        }
    ]
