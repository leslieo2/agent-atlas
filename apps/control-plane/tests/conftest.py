from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from app.bootstrap.container import get_container
from app.bootstrap.wiring import infrastructure as infrastructure_wiring
from app.core.config import RuntimeMode, TraceBackendMode, settings
from app.infrastructure.repositories import reset_state
from fastapi.testclient import TestClient
from tests.support.fake_phoenix import FakeOtlpTraceExporter, FakePhoenixTraceBackend


def _reset_state() -> None:
    get_container.cache_clear()
    reset_state()


@pytest.fixture(autouse=True)
def reset_in_memory_state(monkeypatch) -> None:
    settings.runtime_mode = RuntimeMode.AUTO
    settings.openai_api_key = None
    settings.seed_demo = True
    settings.trace_backend = TraceBackendMode.STATE
    settings.phoenix_base_url = "http://phoenix.test:6006"
    settings.observability_otlp_endpoint = "http://phoenix.test:6006/v1/traces"
    settings.observability_headers = {}
    settings.phoenix_api_key = None
    settings.observability_project_name = "agent-atlas-tests"
    monkeypatch.setattr(infrastructure_wiring, "PhoenixTraceBackend", FakePhoenixTraceBackend)
    monkeypatch.setattr(infrastructure_wiring, "OtlpTraceExporter", FakeOtlpTraceExporter)
    _reset_state()
    yield
    _reset_state()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def wait_until() -> Callable[[Callable[[], bool], float, float], None]:
    def _wait_until(
        predicate: Callable[[], bool],
        timeout: float = 3.0,
        interval: float = 0.05,
    ) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return
            time.sleep(interval)
        raise AssertionError(f"condition not met within {timeout:.2f}s")

    return _wait_until


@pytest.fixture
def worker_drain() -> Callable[[int], int]:
    def _worker_drain(limit: int = 10) -> int:
        worker = get_container().worker.app_worker
        processed = 0
        for _ in range(limit):
            if not worker.run_once("test-worker", lease_seconds=30):
                break
            processed += 1
        return processed

    return _worker_drain


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    root = Path(__file__).parent
    for item in items:
        try:
            relative_path = Path(str(item.fspath)).resolve().relative_to(root.resolve())
        except ValueError:
            continue

        parts = relative_path.parts
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
            continue
        if "integration" in parts:
            item.add_marker(pytest.mark.integration)
            continue
        if "e2e" in parts:
            item.add_marker(pytest.mark.e2e)
            continue

        if relative_path.name == "test_services.py":
            item.add_marker(pytest.mark.unit)
        elif relative_path.name in {"test_runs_api.py", "test_health.py"}:
            item.add_marker(pytest.mark.integration)
