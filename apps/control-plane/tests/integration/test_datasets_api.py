from __future__ import annotations


def test_datasets_api_persists_rl_asset_metadata(client) -> None:
    create_response = client.post(
        "/api/v1/datasets",
        json={
            "name": "rl-curation-set",
            "description": "High-value customer support prompts.",
            "source": "support_ticket_backfill",
            "version": "2026-03-rl-v1",
            "rows": [
                {
                    "sample_id": "sample-001",
                    "input": "customer asks for refund escalation",
                    "expected": "refund policy answer",
                    "tags": ["refund", "escalation"],
                    "slice": "hard-cases",
                    "source": "support_ticket_backfill",
                    "metadata": {"channel": "chat"},
                    "export_eligible": True,
                }
            ],
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "rl-curation-set"
    assert created["description"] == "High-value customer support prompts."
    assert created["source"] == "support_ticket_backfill"
    assert created["version"] == "2026-03-rl-v1"
    assert created["rows"][0]["slice"] == "hard-cases"
    assert created["rows"][0]["metadata"] == {"channel": "chat"}
    assert created["rows"][0]["export_eligible"] is True

    listing_response = client.get("/api/v1/datasets")
    assert listing_response.status_code == 200
    listing = listing_response.json()
    assert any(item["name"] == "rl-curation-set" for item in listing)

    detail_response = client.get("/api/v1/datasets/rl-curation-set")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == "rl-curation-set"
    assert detail["rows"][0]["sample_id"] == "sample-001"
    assert detail["rows"][0]["source"] == "support_ticket_backfill"


def test_datasets_api_can_materialize_the_bundled_claude_code_starter_dataset(client) -> None:
    create_response = client.post("/api/v1/datasets/starters/claude-code")

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "claude-code-code-edit"
    assert created["version"] == "v1"
    assert created["source"] == "claude-code-code-edit-v1"
    assert created["rows"][0]["sample_id"] == "claude-code-edit-sample-1"
    assert created["rows"][0]["tags"] == ["claude-code", "code-edit", "starter"]
    assert created["rows"][0]["export_eligible"] is True

    second_response = client.post("/api/v1/datasets/starters/claude-code")

    assert second_response.status_code == 200
    assert second_response.json()["name"] == "claude-code-code-edit"
    assert second_response.json()["current_version_id"] == created["current_version_id"]
