from __future__ import annotations

from app.core.config import RuntimeMode, Settings
from pydantic import SecretStr


def test_settings_auto_mode_resolves_to_mock_without_api_key():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.AUTO
    settings.openai_api_key = None

    assert settings.effective_runtime_mode() == RuntimeMode.MOCK


def test_settings_auto_mode_resolves_to_live_with_api_key():
    settings = Settings()
    settings.runtime_mode = RuntimeMode.AUTO
    settings.openai_api_key = SecretStr("sk-test")

    assert settings.effective_runtime_mode() == RuntimeMode.LIVE


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
