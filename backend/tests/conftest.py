from __future__ import annotations

from collections import defaultdict

import pytest
from app.db.state import state
from fastapi.testclient import TestClient


def _reset_state() -> None:
    state.runs = {}
    state.trajectory = defaultdict(list)
    state.trace_spans = defaultdict(list)
    state.datasets = {}
    state.eval_jobs = {}
    state.replays = {}
    state.artifacts = {}


@pytest.fixture(autouse=True)
def reset_in_memory_state() -> None:
    _reset_state()
    yield
    _reset_state()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
