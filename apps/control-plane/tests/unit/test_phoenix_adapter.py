from __future__ import annotations

from app.agent_tracing.backends.phoenix import (
    build_phoenix_project_url,
    build_phoenix_trace_url,
)
from app.bootstrap.wiring.infrastructure import (
    _default_phoenix_otlp_endpoint,
    build_infrastructure,
)
from app.core.config import RuntimeMode, settings
from pydantic import SecretStr


def test_build_phoenix_urls():
    project_url = build_phoenix_project_url(
        base_url="http://phoenix.local:6006/",
        project_id="UHJvamVjdDoy",
        experiment_id="exp-123",
        run_id="run-456",
    )
    trace_url = build_phoenix_trace_url(
        base_url="http://phoenix.local:6006/",
        project_id="UHJvamVjdDoy",
        trace_id="abc123",
    )

    assert project_url == (
        "http://phoenix.local:6006/projects/UHJvamVjdDoy?" "experiment_id=exp-123&run_id=run-456"
    )
    assert trace_url == "http://phoenix.local:6006/projects/UHJvamVjdDoy/traces/abc123"


def test_build_phoenix_project_url_falls_back_to_home_without_project_id():
    project_url = build_phoenix_project_url(
        base_url="http://phoenix.local:6006/",
        project_id=None,
        experiment_id="exp-123",
    )

    assert project_url == "http://phoenix.local:6006"


def test_build_infrastructure_defaults_to_state_backend_without_phoenix(monkeypatch):
    monkeypatch.setattr(settings, "phoenix_base_url", None)
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", None)

    infrastructure = build_infrastructure()

    assert infrastructure.tracing.trace_backend.backend_name() == "state"


def test_build_infrastructure_keeps_state_backend_with_phoenix_links(monkeypatch):
    monkeypatch.setattr(settings, "phoenix_base_url", "http://phoenix.local:6006")
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", "http://phoenix.local:6006/v1/traces")

    infrastructure = build_infrastructure()

    assert infrastructure.tracing.trace_backend.backend_name() == "state"
    assert infrastructure.tracing.trace_exporter.backend_name_value == "phoenix"


def test_default_phoenix_otlp_endpoint_uses_standard_trace_path():
    assert (
        _default_phoenix_otlp_endpoint("http://phoenix.local:6006")
        == "http://phoenix.local:6006/v1/traces"
    )
    assert (
        _default_phoenix_otlp_endpoint("http://phoenix.local:6006/")
        == "http://phoenix.local:6006/v1/traces"
    )


def test_build_infrastructure_derives_otlp_endpoint_from_phoenix_base_url(monkeypatch):
    monkeypatch.setattr(settings, "phoenix_base_url", "http://phoenix.local:6006")
    monkeypatch.setattr(settings, "tracing_otlp_endpoint", None)

    infrastructure = build_infrastructure()

    assert infrastructure.tracing.trace_backend.backend_name() == "state"
    assert infrastructure.tracing.trace_exporter.backend_name_value == "phoenix"


def test_build_infrastructure_removes_local_runtime_authority_in_live_mode(monkeypatch):
    monkeypatch.setattr(settings, "runtime_mode", RuntimeMode.LIVE)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-test"))

    infrastructure = build_infrastructure()

    assert infrastructure.execution.default_runner_backend == "k8s-container"
    assert "local-process" not in infrastructure.execution.runner.runners
    assert "local-runner" not in infrastructure.execution.execution_control.backends
