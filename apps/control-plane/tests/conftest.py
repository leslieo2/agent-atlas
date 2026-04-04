from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from app.bootstrap.container import get_container
from app.bootstrap.wiring import infrastructure as infrastructure_wiring
from app.core.config import ExecutionJobBackend, settings
from app.infrastructure.adapters.execution_jobs import InlineExecutionJobQueue
from app.infrastructure.repositories import reset_state
from fastapi.testclient import TestClient
from tests.support.fake_phoenix import FakeOtlpTraceExporter


def _reset_state() -> None:
    get_container.cache_clear()
    reset_state()


@pytest.fixture(autouse=True)
def reset_in_memory_state(monkeypatch) -> None:
    state_dir = TemporaryDirectory(prefix="agent-atlas-tests-")
    state_root = Path(state_dir.name)
    settings.openai_api_key = None
    settings.control_plane_database_url = f"sqlite:///{state_root / 'control-plane-state.db'}"
    settings.data_plane_database_url = f"sqlite:///{state_root / 'data-plane-state.db'}"
    settings.execution_job_backend = ExecutionJobBackend.INLINE
    settings.phoenix_base_url = "http://phoenix.test:6006"
    settings.tracing_otlp_endpoint = "http://phoenix.test:6006/v1/traces"
    settings.tracing_headers = {}
    settings.phoenix_api_key = None
    settings.tracing_project_name = "agent-atlas-tests"
    monkeypatch.setattr(infrastructure_wiring, "OtlpTraceExporter", FakeOtlpTraceExporter)
    _reset_state()
    yield
    _reset_state()
    state_dir.cleanup()


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
        container = get_container()
        job_queue = container.infrastructure.execution.job_queue
        if not isinstance(job_queue, InlineExecutionJobQueue):
            raise AssertionError("tests require InlineExecutionJobQueue")
        return job_queue.drain(handlers=container.jobs.handlers, limit=limit)

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
