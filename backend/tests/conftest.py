from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from app.bootstrap.container import get_container
from app.core.config import RunnerMode, RuntimeMode, settings
from app.infrastructure.repositories import reset_state
from fastapi.testclient import TestClient


def _reset_state() -> None:
    get_container.cache_clear()
    reset_state()


@pytest.fixture(autouse=True)
def reset_in_memory_state() -> None:
    settings.runtime_mode = RuntimeMode.AUTO
    settings.runner_mode = RunnerMode.AUTO
    settings.openai_api_key = None
    settings.seed_demo = True
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
        worker = get_container().app_worker
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
