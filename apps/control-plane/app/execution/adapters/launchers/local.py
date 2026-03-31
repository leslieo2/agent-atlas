from __future__ import annotations

from agent_atlas_contracts.execution import RunnerRunSpec
from agent_atlas_contracts.runtime import (
    PublishedRunExecutionResult,
    empty_artifact_manifest,
    producer_for_runtime,
    terminal_result_from_runtime_result,
    trace_event_to_event_envelope,
)
from agent_atlas_runner_base.launchers import (
    LocalLauncher as RunnerBaseLocalLauncher,
)
from agent_atlas_runner_base.launchers import (
    LocalLaunchSession,
)
from agent_atlas_runner_base.outputs import RunnerOutputWriter


def persist_published_execution(
    payload: RunnerRunSpec,
    result: PublishedRunExecutionResult,
) -> None:
    event_envelopes = list(result.event_envelopes)
    if not event_envelopes and result.trace_events:
        producer = (
            result.terminal_result.producer
            if result.terminal_result is not None
            else producer_for_runtime(
                runtime=result.runtime_result.provider,
                framework=payload.framework,
            )
        )
        event_envelopes = [
            trace_event_to_event_envelope(
                event,
                experiment_id=payload.experiment_id,
                attempt=payload.attempt,
                attempt_id=payload.attempt_id,
                producer=producer,
                sequence=index,
            )
            for index, event in enumerate(result.trace_events, start=1)
        ]

    terminal_result = result.terminal_result
    if terminal_result is None:
        producer = (
            event_envelopes[0].producer
            if event_envelopes
            else producer_for_runtime(
                runtime=result.runtime_result.provider,
                framework=payload.framework,
            )
        )
        terminal_result = terminal_result_from_runtime_result(
            payload=payload,
            runtime_result=result.runtime_result,
            producer=producer,
            tool_calls=sum(1 for event in event_envelopes if event.event_type.startswith("tool.")),
        )

    artifact_manifest = result.artifact_manifest
    if artifact_manifest is None:
        artifact_manifest = empty_artifact_manifest(
            payload=payload,
            producer=terminal_result.producer,
        )

    writer = RunnerOutputWriter(payload.bootstrap)
    writer.write_events(event_envelopes)
    writer.write_runtime_result(result.runtime_result)
    writer.write_terminal_result(terminal_result)
    writer.write_artifact_manifest(artifact_manifest)


class LocalLauncher(RunnerBaseLocalLauncher):
    def persist_result(
        self,
        session: LocalLaunchSession,
        result: PublishedRunExecutionResult,
    ) -> None:
        persist_published_execution(session.payload, result)


__all__ = ["LocalLaunchSession", "LocalLauncher", "persist_published_execution"]
