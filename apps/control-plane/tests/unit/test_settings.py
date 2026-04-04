from __future__ import annotations

import pytest
from app.core.config import Settings
from pydantic import SecretStr


def test_settings_openai_api_key_defaults_to_none():
    settings = Settings()

    assert settings.openai_api_key is None


def test_settings_reads_agent_atlas_openai_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_ATLAS_OPENAI_API_KEY", "sk-canonical")

    settings = Settings()

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-canonical"


def test_settings_ignores_legacy_openai_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AGENT_ATLAS_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy")

    settings = Settings()

    assert settings.openai_api_key is None


def test_settings_accepts_direct_openai_api_key_assignment():
    settings = Settings()
    settings.openai_api_key = SecretStr("sk-test")

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-test"
