from __future__ import annotations

import pytest
from app.core.config import RuntimeMode, Settings
from pydantic import SecretStr


def test_settings_auto_mode_resolves_to_mock_without_api_key():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.AUTO

    assert settings.effective_runtime_mode() == RuntimeMode.MOCK


def test_settings_auto_mode_stays_mock_even_with_openai_key():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.AUTO
    settings.openai_api_key = SecretStr("sk-test")

    assert settings.effective_runtime_mode() == RuntimeMode.MOCK


def test_settings_live_mode_disables_demo_seed_by_default():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.LIVE
    settings.seed_demo = None

    assert settings.should_seed_demo() is False


def test_settings_seed_demo_override_takes_precedence():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.LIVE
    settings.seed_demo = True

    assert settings.should_seed_demo() is True


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
