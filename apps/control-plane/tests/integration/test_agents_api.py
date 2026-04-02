from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.bootstrap.container import get_container
from app.core.config import RuntimeMode, settings
from app.modules.agents.domain.constants import CLAUDE_CODE_CLI_FRAMEWORK
from app.modules.agents.domain.models import (
    AgentManifest,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
)
from app.modules.agents.domain.starter_assets import (
    CLAUDE_CODE_STARTER_AGENT_ID,
    CLAUDE_CODE_STARTER_ENTRYPOINT,
    claude_code_starter_runtime_profile,
)
from app.modules.runs.domain.models import RunRecord
from app.modules.shared.domain.constants import EXTERNAL_RUNNER_EXECUTION_BACKEND
from app.modules.shared.domain.enums import AdapterKind, AgentFamily, RunStatus
from app.modules.shared.domain.models import TracePointer
from fastapi.testclient import TestClient


def test_agents_api_supports_discovery_publish_unpublish_and_invalid_publish(
    monkeypatch, client
) -> None:
    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    discovered = {item["agent_id"]: item for item in discovered_response.json()}

    assert "basic" in discovered
    assert discovered["basic"]["validation_status"] == "valid"
    assert discovered["basic"]["publish_state"] == "published"

    unpublish_response = client.post("/api/v1/agents/tools/unpublish")
    assert unpublish_response.status_code == 200
    assert unpublish_response.json() == {"agent_id": "tools", "published": False}

    after_unpublish = client.get("/api/v1/agents/discovered")
    assert after_unpublish.status_code == 200
    discovered_after_unpublish = {item["agent_id"]: item for item in after_unpublish.json()}
    assert discovered_after_unpublish["tools"]["publish_state"] == "draft"

    publish_response = client.post("/api/v1/agents/tools/publish")
    assert publish_response.status_code == 200
    assert publish_response.json()["agent_id"] == "tools"

    invalid_agent = DiscoveredAgent(
        manifest=AgentManifest(
            agent_id="broken",
            name="Broken",
            description="Broken plugin",
            framework="openai-agents-sdk",
            default_model="gpt-5.4-mini",
            tags=[],
        ),
        entrypoint="app.agent_plugins.broken:build_agent",
        validation_status=AgentValidationStatus.INVALID,
        validation_issues=[
            AgentValidationIssue(code="manifest_missing", message="missing AGENT_MANIFEST"),
        ],
    )

    monkeypatch.setattr(
        get_container().agents.agent_publication_commands.discovery,
        "list_agents",
        lambda: [invalid_agent],
    )

    invalid_publish_response = client.post("/api/v1/agents/broken/publish")
    assert invalid_publish_response.status_code == 400
    assert invalid_publish_response.json()["detail"]["code"] == "agent_validation_failed"
    assert invalid_publish_response.json()["detail"]["agent_id"] == "broken"


def test_agents_api_lists_published_snapshots_even_when_not_discoverable(client) -> None:
    container = get_container()
    published_agent = container.infrastructure.published_agent_repository.get_agent("basic")
    assert published_agent is not None

    published_only = published_agent.model_copy(
        update={
            "manifest": published_agent.manifest.model_copy(update={"agent_id": "archived-basic"}),
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(published_only)

    list_response = client.get("/api/v1/agents/published")
    assert list_response.status_code == 200
    published = {item["agent_id"]: item for item in list_response.json()}

    assert "archived-basic" not in published


def test_agents_api_skips_legacy_published_rows_in_list_endpoints(client) -> None:
    container = get_container()
    published_agent = container.infrastructure.published_agent_repository.get_agent("basic")
    assert published_agent is not None

    legacy = published_agent.model_copy(
        update={
            "manifest": published_agent.manifest.model_copy(update={"agent_id": "legacy-basic"}),
            "source_fingerprint": "",
            "execution_reference": {"artifact_ref": None, "image_ref": None},
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(legacy)

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert "legacy-basic" not in published

    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    discovered = {item["agent_id"]: item for item in discovered_response.json()}
    assert discovered["basic"]["publish_state"] == "published"


def test_agents_api_treats_corrupt_matching_publication_as_unpublished_in_discovery(client) -> None:
    container = get_container()
    published_agent = container.infrastructure.published_agent_repository.get_agent("basic")
    assert published_agent is not None

    corrupted = published_agent.model_copy(
        update={
            "source_fingerprint": "",
            "execution_reference": {"artifact_ref": None, "image_ref": None},
        },
        deep=True,
    )
    container.infrastructure.published_agent_repository.save_agent(corrupted)

    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    discovered = {item["agent_id"]: item for item in discovered_response.json()}
    assert discovered["basic"]["publish_state"] == "draft"
    assert discovered["basic"]["execution_reference"] is None


def test_unpublish_returns_404_for_missing_published_agent(client) -> None:
    response = client.post("/api/v1/agents/not-published/unpublish")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "published_agent_not_found",
        "message": "published agent 'not-published' was not found",
        "agent_id": "not-published",
    }


def test_agents_api_live_mode_uses_published_snapshots_without_repo_local_discovery(
    monkeypatch,
    client,
) -> None:
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    get_container.cache_clear()

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert "basic" in published

    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    assert discovered_response.json() == []

    publish_response = client.post("/api/v1/agents/basic/publish")
    assert publish_response.status_code == 400
    assert publish_response.json()["detail"] == {
        "code": "agent_validation_failed",
        "message": "agent 'basic' is not available in the current discovery catalog",
        "agent_id": "basic",
    }


def test_agents_api_live_mode_supports_first_agent_bootstrap_without_repo_discovery(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "seed_demo", False)
    get_container.cache_clear()
    from app.main import app

    with TestClient(app) as live_client:
        published_response = live_client.get("/api/v1/agents/published")
        assert published_response.status_code == 200
        assert published_response.json() == []

        discovered_response = live_client.get("/api/v1/agents/discovered")
        assert discovered_response.status_code == 200
        assert discovered_response.json() == []

        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["agent_id"] == "claude-code-starter"
        assert bootstrap_response.json()["entrypoint"] == CLAUDE_CODE_STARTER_ENTRYPOINT
        assert bootstrap_response.json()["agent_family"] == AgentFamily.CLAUDE_CODE.value
        assert bootstrap_response.json()["framework"] == CLAUDE_CODE_CLI_FRAMEWORK
        assert (
            bootstrap_response.json()["default_runtime_profile"]["backend"]
            == EXTERNAL_RUNNER_EXECUTION_BACKEND
        )
        assert (
            bootstrap_response.json()["default_runtime_profile"]["metadata"]["claude_code_cli"][
                "system_prompt"
            ]
            == "Reply with the user prompt text only. No greeting or explanation."
        )

        published_after_bootstrap = live_client.get("/api/v1/agents/published")
        assert published_after_bootstrap.status_code == 200
        published = {item["agent_id"]: item for item in published_after_bootstrap.json()}
        assert published["claude-code-starter"]["source_fingerprint"]
        assert (
            published["claude-code-starter"]["execution_reference"]["artifact_ref"]
            == f"source://claude-code-starter@{published['claude-code-starter']['source_fingerprint']}"
        )

        second_bootstrap = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert second_bootstrap.status_code == 200
        assert second_bootstrap.json()["agent_id"] == "claude-code-starter"


def test_agents_api_live_mode_bootstrap_keeps_starter_reachable_for_publish_and_drift(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "seed_demo", False)
    get_container.cache_clear()
    from app.main import app

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        discovered_after_bootstrap = live_client.get("/api/v1/agents/discovered")
        assert discovered_after_bootstrap.status_code == 200
        discovered = {item["agent_id"]: item for item in discovered_after_bootstrap.json()}
        assert discovered[CLAUDE_CODE_STARTER_AGENT_ID]["publish_state"] == "published"
        assert discovered[CLAUDE_CODE_STARTER_AGENT_ID]["has_unpublished_changes"] is False

        unpublish_response = live_client.post("/api/v1/agents/claude-code-starter/unpublish")
        assert unpublish_response.status_code == 200

        discovered_after_unpublish = live_client.get("/api/v1/agents/discovered")
        assert discovered_after_unpublish.status_code == 200
        discovered = {item["agent_id"]: item for item in discovered_after_unpublish.json()}
        assert discovered[CLAUDE_CODE_STARTER_AGENT_ID]["publish_state"] == "draft"
        assert (
            discovered[CLAUDE_CODE_STARTER_AGENT_ID]["default_runtime_profile"]["runner_image"]
            == "atlas-claude-validation:local"
        )

        republish_response = live_client.post("/api/v1/agents/claude-code-starter/publish")
        assert republish_response.status_code == 200
        assert republish_response.json()["agent_id"] == CLAUDE_CODE_STARTER_AGENT_ID

        container = get_container()
        published = container.infrastructure.published_agent_repository.get_agent(
            CLAUDE_CODE_STARTER_AGENT_ID
        )
        assert published is not None
        stale = published.model_copy(
            update={"source_fingerprint": "stale-starter-fingerprint"},
            deep=True,
        )
        container.infrastructure.published_agent_repository.save_agent(stale)

        discovered_after_drift = live_client.get("/api/v1/agents/discovered")
        assert discovered_after_drift.status_code == 200
        discovered = {item["agent_id"]: item for item in discovered_after_drift.json()}
        assert discovered[CLAUDE_CODE_STARTER_AGENT_ID]["publish_state"] == "published"
        assert discovered[CLAUDE_CODE_STARTER_AGENT_ID]["has_unpublished_changes"] is True


def test_agents_api_live_mode_validation_runs_accept_state_backed_starter_drafts(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "seed_demo", False)
    get_container.cache_clear()
    from app.main import app

    with TestClient(app) as live_client:
        bootstrap_response = live_client.post("/api/v1/agents/bootstrap/claude-code")
        assert bootstrap_response.status_code == 200

        unpublish_response = live_client.post("/api/v1/agents/claude-code-starter/unpublish")
        assert unpublish_response.status_code == 200

        response = live_client.post(
            "/api/v1/agents/claude-code-starter/validation-runs",
            json={
                "project": "atlas-validation",
                "dataset": "controlled-validation",
                "input_summary": "Validate the starter from the Agents surface",
                "prompt": "alpha",
                "tags": ["agents-surface"],
                "project_metadata": {"validation_surface": "agents"},
                "executor_config": claude_code_starter_runtime_profile().model_dump(mode="json"),
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["agent_id"] == CLAUDE_CODE_STARTER_AGENT_ID
        assert payload["status"] == "queued"
        assert set(payload["tags"]) >= {"validation", "agents-surface"}
        assert payload["executor_backend"] == "external-runner"
        assert payload["provenance"]["published_agent_snapshot"]["manifest"]["agent_id"] == (
            CLAUDE_CODE_STARTER_AGENT_ID
        )


def test_agents_api_surfaces_latest_generic_validation_run_summary(client) -> None:
    container = get_container()
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

    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    discovered = {item["agent_id"]: item for item in discovered_response.json()}

    assert discovered["basic"]["latest_validation"] == {
        "run_id": str(run.run_id),
        "status": "succeeded",
        "created_at": "2026-04-01T16:00:00Z",
        "started_at": "2026-04-01T16:01:00Z",
        "completed_at": "2026-04-01T16:02:00Z",
    }
    assert discovered["basic"]["validation_evidence"] == {
        "artifact_ref": "state://artifacts/validation-run",
        "image_ref": "docker://atlas-claude-validation:local",
        "trace_url": "https://phoenix.example/trace/validation",
        "terminal_summary": None,
    }
    assert discovered["basic"]["validation_outcome"] == {
        "status": "passed",
        "reason": None,
    }

    published_response = client.get("/api/v1/agents/published")
    assert published_response.status_code == 200
    published = {item["agent_id"]: item for item in published_response.json()}
    assert published["basic"]["latest_validation"]["run_id"] == str(run.run_id)


def test_agents_api_ignores_non_validation_runs_in_agent_records(client) -> None:
    container = get_container()
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

    discovered_response = client.get("/api/v1/agents/discovered")
    assert discovered_response.status_code == 200
    discovered = {item["agent_id"]: item for item in discovered_response.json()}

    assert discovered["basic"]["latest_validation"] is None
    assert discovered["basic"]["validation_evidence"] is None
    assert discovered["basic"]["validation_outcome"] is None


def test_agents_api_starts_generic_validation_runs_via_agent_entrypoint(client) -> None:
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
    assert payload["provenance"]["executor"]["metadata"]["runner_backend"] == "k8s-container"
