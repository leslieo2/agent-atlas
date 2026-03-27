from __future__ import annotations

from app.bootstrap.container import get_container
from app.modules.traces.application.use_cases import TraceCommands


def get_trace_commands() -> TraceCommands:
    return get_container().traces.trace_commands
