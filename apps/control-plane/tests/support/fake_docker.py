from __future__ import annotations

from app.execution.adapters.runner import DockerContainerRunner
from app.execution.application.results import (
    PublishedRunExecutionResult,
    RunnerExecutionResult,
    RuntimeExecutionResult,
)
from app.modules.shared.domain.enums import StepType
from app.modules.shared.domain.traces import TraceIngestEvent


def install_fake_docker_runtime(monkeypatch, *, outputs: dict[str, str]) -> None:
    def execute(payload):
        output = outputs.get(payload.prompt, payload.prompt)
        image = payload.executor_config.get("runner_image")
        return RunnerExecutionResult(
            runner_backend="docker-container",
            artifact_ref=payload.artifact_ref,
            image_ref=payload.image_ref,
            execution=PublishedRunExecutionResult(
                runtime_result=RuntimeExecutionResult(
                    output=output,
                    latency_ms=12,
                    token_usage=21,
                    provider="claude-code-cli",
                    execution_backend="external-runner",
                    container_image=image if isinstance(image, str) else None,
                    resolved_model=payload.model,
                ),
                trace_events=[
                    TraceIngestEvent(
                        run_id=payload.run_id,
                        span_id=f"span-{payload.run_id}-1",
                        step_type=StepType.LLM,
                        name=payload.model or "claude-code-cli",
                        input={"prompt": payload.prompt},
                        output={"output": output, "success": True},
                    )
                ],
            ),
        )

    monkeypatch.setattr(DockerContainerRunner, "execute", lambda self, payload: execute(payload))
