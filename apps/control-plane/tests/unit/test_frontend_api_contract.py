from __future__ import annotations

from pathlib import Path

import pytest
from scripts.generate_frontend_contract import render_contract_source

ROOT = Path(__file__).resolve().parents[4]
FRONTEND_CONTRACT_PATH = ROOT / "apps" / "web" / "src" / "shared" / "api" / "contract.ts"


def test_generated_frontend_api_contract_is_current() -> None:
    assert FRONTEND_CONTRACT_PATH.exists(), "frontend API contract file is missing"
    assert FRONTEND_CONTRACT_PATH.read_text(encoding="utf-8") == render_contract_source(), (
        "frontend API contract is stale; "
        "run apps/control-plane/scripts/generate_frontend_contract.py"
    )


def test_generated_frontend_api_contract_uses_valid_typescript_identifiers(
    monkeypatch,
) -> None:
    def fake_openapi() -> dict[str, object]:
        return {
            "components": {
                "schemas": {
                    "ApprovalPolicySnapshot-Input": {"type": "string"},
                    "ApprovalPolicySnapshot-Output": {"type": "string"},
                }
            }
        }

    monkeypatch.setattr("scripts.generate_frontend_contract.app.openapi", fake_openapi)

    rendered = render_contract_source()
    assert "ApprovalPolicySnapshot_Input" in rendered
    assert "ApprovalPolicySnapshot_Output" in rendered
    assert "ApprovalPolicySnapshot-Input" not in rendered
    assert "ApprovalPolicySnapshot-Output" not in rendered


def test_generated_frontend_api_contract_fails_fast_on_identifier_collisions(
    monkeypatch,
) -> None:
    def fake_openapi() -> dict[str, object]:
        return {
            "components": {
                "schemas": {
                    "Foo-Bar": {"type": "string"},
                    "Foo_Bar": {"type": "string"},
                }
            }
        }

    monkeypatch.setattr("scripts.generate_frontend_contract.app.openapi", fake_openapi)

    with pytest.raises(ValueError, match="collide after TypeScript identifier normalization"):
        render_contract_source()
