from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.agents.domain.models import (
    AgentManifest,
    AgentValidationIssue,
    AgentValidationStatus,
    DiscoveredAgent,
)


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

    assert "archived-basic" in published
    assert published["archived-basic"]["entrypoint"] == published_only.entrypoint


def test_unpublish_returns_404_for_missing_published_agent(client) -> None:
    response = client.post("/api/v1/agents/not-published/unpublish")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "published_agent_not_found",
        "message": "published agent 'not-published' was not found",
        "agent_id": "not-published",
    }
