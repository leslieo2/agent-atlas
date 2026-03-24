from __future__ import annotations

from app.services import runner


def test_runner_prefers_docker_when_available_in_auto_mode(monkeypatch):
    monkeypatch.setattr(runner.settings, "runner_mode", "auto")
    monkeypatch.setattr(runner.DockerRunner, "is_available", lambda self: True)

    ordered = runner._ordered_runners()

    assert ordered[0].name == "docker"
    assert ordered[1].name == "local"


def test_runner_falls_back_to_mock_when_mode_is_mock(monkeypatch):
    monkeypatch.setattr(runner.settings, "runner_mode", "mock")

    ordered = runner._ordered_runners()

    assert len(ordered) == 1
    assert ordered[0].name == "mock"
