from __future__ import annotations

from uuid import uuid4

from app.agent_plugins.fulfillment_ops import ToolBackendError
from app.bootstrap.container import get_container
from app.core.errors import ProviderAuthError
from app.modules.agents.domain.models import (
    AgentManifest,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
)
from app.modules.runs.application.results import PublishedRunExecutionResult
from app.modules.runs.domain.models import RuntimeExecutionResult
from app.modules.shared.domain.enums import RunStatus, StepType
from app.modules.traces.domain.models import TraceIngestEvent


def test_runs_api_create_list_and_trajectory_filters(monkeypatch, client, worker_drain):
    container = get_container()
    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        lambda *_args, **_kwargs: PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="mocked integration output",
                latency_ms=1,
                token_usage=1,
                provider="mock",
                resolved_model="gpt-5.4-mini",
            )
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


def test_runs_api_persists_tool_steps_from_runtime_trace_events(monkeypatch, client, worker_drain):
    container = get_container()

    def execute_published(run_id, payload):
        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="ETA is 2 business days.",
                latency_ms=4,
                token_usage=19,
                provider="openai-agents-sdk",
                resolved_model="gpt-5.4-mini",
            ),
            trace_events=[
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-1",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={"prompt": payload.prompt, "model": "gpt-5.4-mini"},
                    output={
                        "output": (
                            'tool_call: lookup_shipping_window({"order_reference":"A-1024"})'
                        )
                    },
                    token_usage=7,
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-2",
                    parent_span_id=f"span-{run_id}-1",
                    step_type=StepType.TOOL,
                    name="lookup_shipping_window",
                    input={"prompt": '{"order_reference":"A-1024"}'},
                    output={"output": "eta_window=2 business days"},
                    tool_name="lookup_shipping_window",
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-3",
                    parent_span_id=f"span-{run_id}-2",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={
                        "prompt": (
                            f"{payload.prompt}\n\nTool outputs:\n"
                            "lookup_shipping_window: eta_window=2 business days"
                        )
                    },
                    output={"output": "ETA is 2 business days."},
                    token_usage=12,
                ),
            ],
        )

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration-tools",
            "agent_id": "tools",
            "input_summary": "tool trace",
            "prompt": "Use the available tools to look up the shipping window for order A-1024.",
            "tags": ["integration", "tools"],
        },
    )
    assert response.status_code == 201

    run_id = response.json()["run_id"]
    assert worker_drain() >= 1

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    payload = trajectory.json()

    assert [step["step_type"] for step in payload] == ["llm", "tool", "llm"]
    assert payload[1]["tool_name"] == "lookup_shipping_window"
    assert payload[1]["parent_step_id"] == payload[0]["id"]
    assert payload[2]["parent_step_id"] == payload[1]["id"]

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json()["tool_calls"] == 1


def test_runs_api_persists_multi_tool_trajectory_for_fulfillment_ops(
    monkeypatch, client, worker_drain
):
    container = get_container()

    def execute_published(run_id, payload):
        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="resolved: reship_order",
                latency_ms=6,
                token_usage=33,
                provider="openai-agents-sdk",
                resolved_model="gpt-5.4-mini",
            ),
            trace_events=[
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-1",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={"prompt": payload.prompt, "model": "gpt-5.4-mini"},
                    output={
                        "output": (
                            'tool_call: lookup_order_status({"order_id":"ORD-1002"})\n'
                            'tool_call: lookup_inventory({"sku":"SKU-ALPHA"})'
                        )
                    },
                    token_usage=11,
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-2",
                    parent_span_id=f"span-{run_id}-1",
                    step_type=StepType.TOOL,
                    name="lookup_order_status",
                    input={"prompt": '{"order_id":"ORD-1002"}'},
                    output={
                        "output": (
                            "order_id=ORD-1002; status=lost_in_transit; shipment_state=exception; "
                            "sku=SKU-ALPHA; issue_type=lost_package; priority=priority; "
                            "reship_allowed=yes"
                        )
                    },
                    tool_name="lookup_order_status",
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-3",
                    parent_span_id=f"span-{run_id}-2",
                    step_type=StepType.TOOL,
                    name="lookup_inventory",
                    input={"prompt": '{"sku":"SKU-ALPHA"}'},
                    output={
                        "output": "sku=SKU-ALPHA; stock_state=in_stock; replacement_available=yes"
                    },
                    tool_name="lookup_inventory",
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-4",
                    parent_span_id=f"span-{run_id}-3",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={
                        "prompt": (
                            f"{payload.prompt}\n\nTool outputs:\n"
                            "lookup_order_status: order_id=ORD-1002; status=lost_in_transit; "
                            "shipment_state=exception; sku=SKU-ALPHA; issue_type=lost_package; "
                            "priority=priority; reship_allowed=yes\n"
                            "lookup_inventory: sku=SKU-ALPHA; stock_state=in_stock; "
                            "replacement_available=yes"
                        )
                    },
                    output={"output": "resolved: reship_order"},
                    token_usage=22,
                ),
            ],
        )

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration-fulfillment",
            "dataset": "fulfillment-eval-v1",
            "agent_id": "fulfillment_ops",
            "input_summary": "fulfillment multi-tool trace",
            "prompt": (
                "Order ORD-1002 is missing in transit. "
                "Check inventory and decide the next action."
            ),
            "tags": ["integration", "fulfillment"],
        },
    )
    assert response.status_code == 201

    run_id = response.json()["run_id"]
    assert worker_drain() >= 1

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    payload = trajectory.json()

    assert [step["step_type"] for step in payload] == ["llm", "tool", "tool", "llm"]
    assert [step["tool_name"] for step in payload if step["step_type"] == "tool"] == [
        "lookup_order_status",
        "lookup_inventory",
    ]
    assert payload[1]["parent_step_id"] == payload[0]["id"]
    assert payload[2]["parent_step_id"] == payload[1]["id"]
    assert payload[3]["parent_step_id"] == payload[2]["id"]

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json()["tool_calls"] == 2
    assert run_state.json()["entrypoint"] == "app.agent_plugins.fulfillment_ops:build_agent"


def test_runs_api_exposes_structured_failure_details(monkeypatch, client, worker_drain):
    container = get_container()

    def execute_published(*_args, **_kwargs):
        raise ProviderAuthError("provider authentication failed")

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration-failure",
            "agent_id": "basic",
            "input_summary": "structured failure",
            "prompt": "Trigger a provider auth failure.",
            "tags": ["integration", "failure"],
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["entrypoint"] == "app.agent_plugins.basic:build_agent"

    run_id = created["run_id"]
    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json() == {
        **run_state.json(),
        "run_id": run_id,
        "status": "failed",
        "entrypoint": "app.agent_plugins.basic:build_agent",
        "execution_backend": None,
        "container_image": None,
        "resolved_model": None,
        "error_code": "provider_call",
        "error_message": "provider authentication failed",
        "termination_reason": "provider authentication failed",
    }


def test_runs_api_maps_fulfillment_tool_failures_to_tool_execution(
    monkeypatch, client, worker_drain
):
    container = get_container()

    def execute_published(*_args, **_kwargs):
        raise ToolBackendError("tool backend unavailable for order 'ORD-ERR-100'")

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration-fulfillment-failure",
            "dataset": "fulfillment-eval-v1",
            "agent_id": "fulfillment_ops",
            "input_summary": "tool execution failure",
            "prompt": "Order ORD-ERR-100 is delayed. Check status and decide the next action.",
            "tags": ["integration", "fulfillment", "runtime-error"],
        },
    )
    assert response.status_code == 201

    run_id = response.json()["run_id"]
    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json() == {
        **run_state.json(),
        "run_id": run_id,
        "status": "failed",
        "entrypoint": "app.agent_plugins.fulfillment_ops:build_agent",
        "execution_backend": None,
        "container_image": None,
        "resolved_model": None,
        "error_code": "tool_execution",
        "error_message": "tool backend unavailable for order 'ORD-ERR-100'",
        "termination_reason": "tool backend unavailable for order 'ORD-ERR-100'",
    }


def test_runs_api_marks_failed_trace_events_as_tool_execution(monkeypatch, client, worker_drain):
    container = get_container()

    def execute_published(run_id, payload):
        return PublishedRunExecutionResult(
            runtime_result=RuntimeExecutionResult(
                output="success",
                latency_ms=5,
                token_usage=14,
                provider="openai-agents-sdk",
                resolved_model="gpt-5.4-mini",
            ),
            trace_events=[
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-1",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={"prompt": payload.prompt, "model": "gpt-5.4-mini"},
                    output={
                        "output": 'tool_call: lookup_order_status({"order_id":"ORD-ERR-100"})',
                        "success": True,
                    },
                    token_usage=6,
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-2",
                    parent_span_id=f"span-{run_id}-1",
                    step_type=StepType.TOOL,
                    name="lookup_order_status",
                    input={"prompt": '{"order_id":"ORD-ERR-100"}'},
                    output={
                        "output": (
                            "An error occurred while running the tool. Please try again. "
                            "Error: tool backend unavailable for order 'ORD-ERR-100'"
                        ),
                        "success": False,
                        "error": "tool backend unavailable for order 'ORD-ERR-100'",
                    },
                    tool_name="lookup_order_status",
                ),
                TraceIngestEvent(
                    run_id=run_id,
                    span_id=f"span-{run_id}-3",
                    parent_span_id=f"span-{run_id}-2",
                    step_type=StepType.LLM,
                    name="gpt-5.4-mini",
                    input={
                        "prompt": (
                            f"{payload.prompt}\n\nTool outputs:\nlookup_order_status: An error "
                            "occurred while running the tool. Please try again. Error: tool "
                            "backend unavailable for order 'ORD-ERR-100'"
                        )
                    },
                    output={
                        "output": "success",
                        "success": False,
                        "error": "tool backend unavailable for order 'ORD-ERR-100'",
                    },
                    token_usage=8,
                ),
            ],
        )

    monkeypatch.setattr(
        container.infrastructure.model_runtime,
        "execute_published",
        execute_published,
    )

    response = client.post(
        "/api/v1/runs",
        json={
            "project": "integration-fulfillment-trace-failure",
            "dataset": "fulfillment-eval-v1",
            "agent_id": "fulfillment_ops",
            "input_summary": "tool execution failure from trace events",
            "prompt": "Order ORD-ERR-100 is delayed. Check status and decide the next action.",
            "tags": ["integration", "fulfillment", "runtime-error"],
        },
    )
    assert response.status_code == 201

    run_id = response.json()["run_id"]
    assert worker_drain() >= 1

    run_state = client.get(f"/api/v1/runs/{run_id}")
    assert run_state.status_code == 200
    assert run_state.json() == {
        **run_state.json(),
        "run_id": run_id,
        "status": "failed",
        "entrypoint": "app.agent_plugins.fulfillment_ops:build_agent",
        "execution_backend": None,
        "container_image": None,
        "resolved_model": "gpt-5.4-mini",
        "error_code": "tool_execution",
        "error_message": "tool backend unavailable for order 'ORD-ERR-100'",
        "termination_reason": "tool backend unavailable for order 'ORD-ERR-100'",
    }

    trajectory = client.get(f"/api/v1/runs/{run_id}/trajectory")
    assert trajectory.status_code == 200
    assert [step["success"] for step in trajectory.json()] == [True, False, False]


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
        "fulfillment_ops",
        "tools",
    }


def test_agents_discovered_publish_and_unpublish_flow(client):
    container = get_container()
    assert container.agents.agent_publication_commands.unpublish("tools") is True

    discovered = client.get("/api/v1/agents/discovered")
    assert discovered.status_code == 200
    by_id = {agent["agent_id"]: agent for agent in discovered.json()}
    assert by_id["tools"]["publish_state"] == "draft"
    assert by_id["tools"]["validation_status"] == "valid"
    assert by_id["tools"]["published_at"] is None
    assert by_id["tools"]["has_unpublished_changes"] is False
    assert by_id["tools"]["last_validated_at"].endswith("Z")

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


def test_discovered_agents_flag_published_drift(monkeypatch, client):
    container = get_container()

    monkeypatch.setattr(
        container.infrastructure.agent_discovery,
        "list_agents",
        lambda: [
            DiscoveredAgent(
                manifest=AgentManifest(
                    agent_id="basic",
                    name="Basic",
                    description="Basic smoke agent",
                    default_model="gpt-4.1",
                    tags=["example", "smoke", "drifted"],
                ),
                entrypoint="app.agent_plugins.basic_v2:build_agent",
                validation_status=AgentValidationStatus.VALID,
            )
        ],
    )

    discovered = client.get("/api/v1/agents/discovered")
    assert discovered.status_code == 200
    assert len(discovered.json()) == 1
    payload = discovered.json()[0]
    assert payload["agent_id"] == "basic"
    assert payload["name"] == "Basic"
    assert payload["description"] == "Basic smoke agent"
    assert payload["framework"] == "openai-agents-sdk"
    assert payload["entrypoint"] == "app.agent_plugins.basic_v2:build_agent"
    assert payload["default_model"] == "gpt-4.1"
    assert payload["tags"] == ["example", "smoke", "drifted"]
    assert payload["publish_state"] == "published"
    assert payload["validation_status"] == "valid"
    assert payload["validation_issues"] == []
    assert isinstance(payload["published_at"], str) and payload["published_at"].endswith("Z")
    assert isinstance(payload["last_validated_at"], str) and payload["last_validated_at"].endswith(
        "Z"
    )
    assert payload["has_unpublished_changes"] is True


def test_runs_reject_unpublished_agent(client):
    container = get_container()
    assert container.agents.agent_publication_commands.unpublish("basic") is True

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
        container.infrastructure.agent_discovery,
        "list_agents",
        lambda: [
            DiscoveredAgent(
                manifest=AgentManifest(
                    agent_id="basic",
                    name="Basic",
                    description="Minimal plugin agent for smoke testing the SDK execution path.",
                    default_model="gpt-5.4-mini",
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
    assert len(discovered.json()) == 1
    payload = discovered.json()[0]
    assert payload["agent_id"] == "basic"
    assert payload["name"] == "Basic"
    assert (
        payload["description"] == "Minimal plugin agent for smoke testing the SDK execution path."
    )
    assert payload["framework"] == "openai-agents-sdk"
    assert payload["entrypoint"] == "app.agent_plugins.basic:build_agent"
    assert payload["default_model"] == "gpt-5.4-mini"
    assert payload["tags"] == ["example", "smoke"]
    assert payload["publish_state"] == "published"
    assert payload["validation_status"] == "invalid"
    assert payload["validation_issues"] == [
        {
            "code": "build_agent_failed",
            "message": "entrypoint validation failed",
        }
    ]
    assert isinstance(payload["published_at"], str) and payload["published_at"].endswith("Z")
    assert isinstance(payload["last_validated_at"], str) and payload["last_validated_at"].endswith(
        "Z"
    )
    assert payload["has_unpublished_changes"] is False
