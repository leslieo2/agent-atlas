from __future__ import annotations

from app.bootstrap.bundles import InfrastructureBundle, TraceModuleBundle
from app.modules.traces.application.use_cases import (
    TraceCommands,
    TraceIngestionWorkflow,
    TraceRecorder,
)


def build_trace_module(infra: InfrastructureBundle) -> TraceModuleBundle:
    trace_workflow = TraceIngestionWorkflow(
        trace_projector=infra.trace_projector,
        trace_recorder=TraceRecorder(trace_repository=infra.trace_repository),
    )
    trace_commands = TraceCommands(workflow=trace_workflow)

    return TraceModuleBundle(
        trace_workflow=trace_workflow,
        trace_commands=trace_commands,
    )
