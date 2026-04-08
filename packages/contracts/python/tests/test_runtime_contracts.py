from __future__ import annotations

from uuid import UUID

from agent_atlas_contracts.execution import RunnerRunSpec
from agent_atlas_contracts.runtime import (
    StepType,
    TraceIngestEvent,
    TraceTelemetryMetadata,
    event_envelope_to_trace_event,
    extract_error_message,
    producer_for_runtime,
    trace_event_to_event_envelope,
    usage_total_tokens,
)


def test_trace_event_round_trip_preserves_metadata_and_payload() -> None:
    trace_event = TraceIngestEvent(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        span_id="span-1",
        parent_span_id="parent-span",
        step_type=StepType.TOOL,
        name="search",
        input={"prompt": "find account"},
        output={"output": "ok", "success": True},
        tool_name="search",
        latency_ms=14,
        token_usage=23,
        metadata=TraceTelemetryMetadata(
            agent_id="basic",
            framework="openai-agents-sdk",
            prompt_version="v1",
        ),
    )

    envelope = trace_event_to_event_envelope(
        trace_event,
        experiment_id=UUID("22222222-2222-2222-2222-222222222222"),
        attempt=2,
        attempt_id=UUID("33333333-3333-3333-3333-333333333333"),
        producer=producer_for_runtime(runtime="openai-agents-sdk"),
        sequence=9,
    )
    restored = event_envelope_to_trace_event(envelope)

    assert restored is not None
    assert restored.run_id == trace_event.run_id
    assert restored.parent_span_id == "parent-span"
    assert restored.step_type is StepType.TOOL
    assert restored.tool_name == "search"
    assert restored.output == {"output": "ok", "success": True}
    assert restored.metadata is not None
    assert restored.metadata.agent_id == "basic"
    assert restored.metadata.prompt_version == "v1"


def test_runner_run_spec_serializes_with_bootstrap_paths() -> None:
    payload = RunnerRunSpec(
        run_id=UUID("11111111-1111-1111-1111-111111111111"),
        runner_backend="local-process",
        project="atlas-validation",
        dataset="controlled-validation",
        agent_id="basic",
        model="gpt-5.4-mini",
        agent_type="openai-agents",
        prompt="Validate this asset",
        published_agent_snapshot={
            "manifest": {
                "agent_id": "basic",
                "name": "Basic",
                "description": "Fixture",
                "framework": "openai-agents-sdk",
                "default_model": "gpt-5.4-mini",
            },
            "entrypoint": "snapshots/basic:run",
        },
    )

    restored = RunnerRunSpec.model_validate_json(payload.model_dump_json())

    assert restored.bootstrap.run_spec_path == "/workspace/input/run_spec.json"
    assert restored.bootstrap.artifact_dir == "/workspace/output/artifacts"
    assert restored.published_agent_snapshot["manifest"]["agent_id"] == "basic"


def test_runtime_helpers_normalize_usage_and_nested_errors() -> None:
    assert usage_total_tokens({"total_tokens": 19}) == 19
    assert usage_total_tokens(type("Usage", (), {"total_tokens": 7})()) == 7
    assert extract_error_message({"error": {"detail": "permission denied"}}) == "permission denied"

