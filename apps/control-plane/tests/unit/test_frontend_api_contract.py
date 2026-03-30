from __future__ import annotations

from pathlib import Path

from scripts.generate_frontend_contract import render_contract_source

ROOT = Path(__file__).resolve().parents[4]
FRONTEND_CONTRACT_PATH = ROOT / "apps" / "web" / "src" / "shared" / "api" / "contract.ts"


def test_generated_frontend_api_contract_is_current() -> None:
    assert FRONTEND_CONTRACT_PATH.exists(), "frontend API contract file is missing"
    assert FRONTEND_CONTRACT_PATH.read_text(encoding="utf-8") == render_contract_source(), (
        "frontend API contract is stale; "
        "run apps/control-plane/scripts/generate_frontend_contract.py"
    )
