from __future__ import annotations

from collections import defaultdict

from app.infrastructure.repositories.common import state


class StateSystemStatus:
    def state_initialized(self) -> bool:
        return bool(state.runs is not None)

    def persistence_enabled(self) -> bool:
        return bool(state.persist.enabled)


def reset_state() -> None:
    state.persist.reset()
    with state.lock:
        state.runs = {}
        state.trajectory = defaultdict(list)
        state.trace_spans = defaultdict(list)
        state.datasets = {}
        state.eval_jobs = {}
        state.replays = {}
        state.artifacts = {}


__all__ = ["StateSystemStatus", "reset_state"]
