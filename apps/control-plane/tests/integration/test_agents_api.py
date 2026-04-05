from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import app.modules.agents.domain.starter_assets as starter_assets
from app.bootstrap.container import get_container
from app.modules.agents.domain.constants import CLAUDE_CODE_CLI_FRAMEWORK
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_ENTRYPOINT,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, AgentFamily, RunStatus
from app.modules.shared.domain.models import TracePointer
from fastapi.testclient import TestClient
from tests.fixtures.agents import build_fixture_published_agent


def test_agents_api_lists_only_governed_published_assets(client) -> None:
    container = get_container()
    published_agent = build_fixture_published_agent("basic")
    container.infrastructure.published_agent_repository.save_agent(published_agent)

    legacy = published_agent.model_copy(
        update={
            "manifest": published_agent.manifest.model_copy(update={"agent_id": "legacy-basic"}),
            "source_fingerprint": "",
            "execution_reference": {"artifact_ref": None, "image_ref": None},
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(legacy)

    response = client.get("/api/v1/agents/published")

    assert response.status_code == 200
    published = {item["agent_id"]: item for item in response.json()}
    assert "basic" in published
    assert "legacy-basic" not in published


def test_agents_api_excludes_corrupt_publications_from_catalog(client) -> None:
    container = get_container()
    published_agent = build_fixture_published_agent("basic")
    container.infrastructure.published_agent_repository.save_agent(published_agent)

    corrupted = published_agent.model_copy(
        update={
            "source_fingerprint": "",
            "execution_reference": {"artifact_ref": None, "image_ref": None},
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(corrupted)

    response = client.get("/api/v1/agents/published")

    assert response.status_code == 200
    published = {item["agent_id"]: item for item in response.json()}
    assert "basic" not in published


def test_agents_api_imports_explicit_source_into_governed_asset(client) -> None:
    response = client.post(
        "/api/v1/agents/imports",
        json={
            "agent_id": "basic",
            "name": "Basic",
            "description": "Minimal fixture agent for Atlas execution smoke tests.",
            "framework": "openai-agents-sdk",
            "default_model": "gpt-5.4-mini",
            "entrypoint": "tests.fixtures.agents.basic:build_agent",
            "agent_family": "openai-agents",
            "framework_version": "1.0.0",
            "tags": ["example", "import"],
            "capabilities": ["submit"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent_id"] == "basic"
    assert payload["entrypoint"] == "tests.fixtures.agents.basic:build_agent"
    assert payload["source_fingerprint"]
    assert (
        payload["execution_reference"]["artifact_ref"]
        == f"source://basic@{payload['source_fingerprint']}"
    )

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert published["basic"]["entrypoint"] == "tests.fixtures.agents.basic:build_agent"


def test_agents_api_starter_entry_creates_first_governed_claude_asset(
    monkeypatch,
) -> None:
    provision_calls: list[str] = []
    monkeypatch.setattr(
        starter_assets,
        "provision_claude_code_starter_carrier",
        lambda: provision_calls.append("called"),
    )
    get_container.cache_clear()
    from app.main import app

    with TestClient(app) as live_client:
        published_response = live_client.get("/api/v1/agents/published")
        assert published_response.status_code == 200
        assert published_response.json() == []

        bootstrap_response = live_client.post("/api/v1/agents/starters/claude-code")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["agent_id"] == "claude-code-starter"
        assert bootstrap_response.json()["entrypoint"] == CLAUDE_CODE_STARTER_ENTRYPOINT
        assert bootstrap_response.json()["agent_family"] == AgentFamily.CLAUDE_CODE.value
        assert bootstrap_response.json()["framework"] == CLAUDE_CODE_CLI_FRAMEWORK
        assert (
            bootstrap_response.json()["default_runtime_profile"]["backend"]
            == EXTERNAL_RUNNER_EXECUTION_BACKEND
        )
        assert "binding" not in bootstrap_response.json()["default_runtime_profile"]
        assert provision_calls == ["called"]

        published_after_bootstrap = live_client.get("/api/v1/agents/published")
        assert published_after_bootstrap.status_code == 200
        published = {item["agent_id"]: item for item in published_after_bootstrap.json()}
        assert published["claude-code-starter"]["source_fingerprint"]
        assert (
            published["claude-code-starter"]["execution_reference"]["artifact_ref"]
            == f"source://claude-code-starter@{published['claude-code-starter']['source_fingerprint']}"
        )


def test_agents_api_validation_runs_accept_published_formal_agents() -> None:
    get_container().infrastructure.published_agent_repository.save_agent(
        build_fixture_published_agent("basic")
    )
    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agents/basic/validation-runs",
            json={
                "project": "atlas-validation",
                "dataset": "controlled-validation",
                "input_summary": "Validate the agent on a controlled project bundle",
                "prompt": "Edit app.py and report completion.",
                "tags": ["project-in-container"],
                "project_metadata": {"validation_image": "atlas-claude-validation:local"},
                "executor_config": {
                    "backend": "external-runner",
                    "runner_image": "atlas-claude-validation:local",
                    "metadata": {"runner_backend": "k8s-container"},
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["agent_id"] == "basic"
        assert payload["project"] == "atlas-validation"
        assert payload["dataset"] == "controlled-validation"
        assert payload["status"] == "queued"
        assert payload["tags"] == ["validation", "project-in-container"]
        assert payload["executor_backend"] == "external-runner"
        assert payload["provenance"]["executor"]["backend"] == "external-runner"
        assert "binding" not in payload["provenance"]["executor"]


def test_agents_api_surfaces_latest_generic_validation_run_summary(client) -> None:
    container = get_container()
    container.infrastructure.published_agent_repository.save_agent(
        build_fixture_published_agent("basic")
    )
    run = RunRecord(
        run_id=uuid4(),
        attempt_id=uuid4(),
        input_summary="controlled validation",
        status=RunStatus.SUCCEEDED,
        project="atlas-validation",
        dataset="controlled-validation",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type=AdapterKind.OPENAI_AGENTS,
        tags=["validation", "project-in-container"],
        created_at=datetime(2026, 4, 1, 16, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 1, 16, 1, tzinfo=UTC),
        completed_at=datetime(2026, 4, 1, 16, 2, tzinfo=UTC),
        artifact_ref="state://artifacts/validation-run",
        image_ref="docker://atlas-claude-validation:local",
        trace_pointer=TracePointer(
            backend="phoenix",
            trace_url="https://phoenix.example/trace/validation",
        ),
    )
    container.infrastructure.run_repository.save(run)

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert published["basic"]["latest_validation"] == {
        "run_id": str(run.run_id),
        "status": "succeeded",
        "created_at": "2026-04-01T16:00:00Z",
        "started_at": "2026-04-01T16:01:00Z",
        "completed_at": "2026-04-01T16:02:00Z",
    }
    assert published["basic"]["validation_evidence"] == {
        "artifact_ref": "state://artifacts/validation-run",
        "image_ref": "docker://atlas-claude-validation:local",
        "trace_url": "https://phoenix.example/trace/validation",
        "terminal_summary": None,
    }
    assert published["basic"]["validation_outcome"] == {
        "status": "passed",
        "reason": None,
    }


def test_agents_api_ignores_non_validation_runs_in_agent_records(client) -> None:
    container = get_container()
    container.infrastructure.published_agent_repository.save_agent(
        build_fixture_published_agent("basic")
    )
    run = RunRecord(
        run_id=uuid4(),
        attempt_id=uuid4(),
        input_summary="normal production run",
        status=RunStatus.SUCCEEDED,
        project="atlas",
        dataset="prod",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type=AdapterKind.OPENAI_AGENTS,
        tags=["production"],
        created_at=datetime(2026, 4, 1, 16, 5, tzinfo=UTC),
    )
    container.infrastructure.run_repository.save(run)

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert published["basic"]["latest_validation"] is None
