from __future__ import annotations

from datetime import datetime, timezone
import random as _random
from uuid import UUID

from app.db.state import state
from app.models.schemas import (
    RunCreateRequest,
    RunRecord,
    RunStatus,
    StepType,
    TraceSpan,
    TrajectoryStep,
)
from app.services.runner import execute_with_fallback
from app.services.model_runtime import model_runtime_service
from app.services.scheduler import run_scheduler


class RunOrchestrator:
    random = _random

    def create_run(self, payload: RunCreateRequest) -> RunRecord:
        run = RunRecord(
            input_summary=payload.input_summary,
            status=RunStatus.QUEUED,
            project=payload.project,
            dataset=payload.dataset,
            model=payload.model,
            agent_type=payload.agent_type,
            tags=payload.tags,
            project_metadata={
                **payload.project_metadata,
                "prompt": payload.prompt,
                "tool_config": payload.tool_config,
            },
        )
        with state.lock:
            state.runs[run.run_id] = run
            state.save_run(run)
        run_scheduler.submit(run.run_id, lambda: self._execute_run(run.run_id, payload))
        return run

    def list_runs(
        self,
        status: RunStatus | None,
        project: str | None,
        dataset: str | None,
        model: str | None,
        tag: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list[RunRecord]:
        def _to_utc_naive(value: datetime | None) -> datetime | None:
            if not value or value.tzinfo is None:
                return value
            return value.astimezone(timezone.utc).replace(tzinfo=None)

        created_from = _to_utc_naive(created_from)
        created_to = _to_utc_naive(created_to)
        with state.lock:
            runs = list(state.runs.values())
        if status:
            runs = [r for r in runs if r.status == status]
        if project:
            runs = [r for r in runs if r.project == project]
        if dataset:
            runs = [r for r in runs if r.dataset == dataset]
        if model:
            runs = [r for r in runs if r.model == model]
        if tag:
            runs = [r for r in runs if tag in r.tags]
        if created_from:
            runs = [r for r in runs if r.created_at >= created_from]
        if created_to:
            runs = [r for r in runs if r.created_at <= created_to]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def get_run(self, run_id: str | UUID) -> RunRecord | None:
        run_uuid = self._coerce_id(run_id)
        with state.lock:
            run = state.runs.get(run_uuid)
        if not run:
            return None
        return run

    def get_trajectory(self, run_id: str | UUID) -> list[TrajectoryStep]:
        run_uuid = self._coerce_id(run_id)
        return state.copy_trajectory(run_uuid)

    def get_traces(self, run_id: str | UUID) -> list[TraceSpan]:
        run_uuid = self._coerce_id(run_id)
        return state.copy_trace_spans(run_uuid)

    def terminate(self, run_id: str | UUID) -> bool:
        run_uuid = self._coerce_id(run_id)
        with state.lock:
            run = state.runs.get(run_uuid)
            if not run:
                return False
            if run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
                return False
            run.status = RunStatus.FAILED
            run.artifact_ref = None
            run.latency_ms = 0
            run.tool_calls = 0
            state.runs[run_uuid] = run
            state.save_run(run)
            return True

    def _execute_run(self, run_id: UUID, payload: RunCreateRequest) -> None:
        self._set_status(run_id, RunStatus.RUNNING)

        planner_prompt = (
            f"Plan execution flow for dataset {payload.dataset} "
            f"using adapter {payload.agent_type.value}."
        )
        planner_output = f"Single-step live model execution planned for project {payload.project}."
        planner_step = TrajectoryStep(
            id=f"{run_id}-step-1",
            run_id=run_id,
            step_type=StepType.PLANNER,
            prompt=planner_prompt,
            output=planner_output,
            model="planner-v1",
            temperature=0.0,
            latency_ms=1,
            token_usage=0,
            success=True,
        )
        planner_trace = TraceSpan(
            run_id=run_id,
            span_id=f"span-{run_id}-1",
            parent_span_id=None,
            step_type=StepType.PLANNER,
            input={"prompt": planner_prompt, "agent_type": payload.agent_type.value},
            output={"output": planner_output, "success": True},
            tool_name=None,
            latency_ms=planner_step.latency_ms,
            token_usage=planner_step.token_usage,
            image_digest=payload.project_metadata.get("image_digest", "sha256:dev"),
            prompt_version=payload.project_metadata.get("prompt_version", "v1"),
        )
        self._append_step(planner_step)
        self._append_span(planner_trace)
        self._record_metrics(run_id, planner_step.latency_ms, planner_step.token_usage, 0)

        tool_preamble_step = TrajectoryStep(
            id=f"{run_id}-step-2",
            run_id=run_id,
            step_type=StepType.TOOL,
            prompt="Prepare runtime context for execution",
            output="runtime context prepared",
            model="planner-v1",
            temperature=0.0,
            latency_ms=2,
            token_usage=0,
            success=True,
            tool_name="runtime-context",
        )
        tool_preamble_trace = TraceSpan(
            run_id=run_id,
            span_id=f"span-{run_id}-2",
            parent_span_id=planner_trace.span_id,
            step_type=StepType.TOOL,
            input={"type": "preamble"},
            output={"output": tool_preamble_step.output, "success": True},
            tool_name="runtime-context",
            latency_ms=tool_preamble_step.latency_ms,
            token_usage=tool_preamble_step.token_usage,
            image_digest=payload.project_metadata.get("image_digest", "sha256:dev"),
            prompt_version=payload.project_metadata.get("prompt_version", "v1"),
        )
        self._append_step(tool_preamble_step)
        self._append_span(tool_preamble_trace)
        self._record_metrics(run_id, tool_preamble_step.latency_ms, 0, 1)

        should_force_mock = self.random.random() > 0.99
        try:
            result = (
                model_runtime_service._simulate_output(
                    payload.agent_type,
                    payload.model,
                    payload.prompt,
                )
                if should_force_mock
                else execute_with_fallback(
                    payload.agent_type,
                    payload.model,
                    payload.prompt,
                )
            )
            llm_step = TrajectoryStep(
                id=f"{run_id}-step-3",
                run_id=run_id,
                step_type=StepType.LLM,
                prompt=payload.prompt,
                output=result["output"],
                model=payload.model,
                temperature=0.0,
                latency_ms=result["latency_ms"],
                token_usage=result["token_usage"],
                success=True,
            )
            llm_trace = TraceSpan(
                run_id=run_id,
                span_id=f"span-{run_id}-3",
                parent_span_id=planner_trace.span_id,
                step_type=StepType.LLM,
                input={"prompt": payload.prompt, "model": payload.model},
                output={"output": llm_step.output, "success": True, "provider": result["provider"]},
                tool_name=None,
                latency_ms=llm_step.latency_ms,
                token_usage=llm_step.token_usage,
                image_digest=result.get("container_image")
                or payload.project_metadata.get("image_digest", "sha256:dev"),
                prompt_version=payload.project_metadata.get("prompt_version", "v1"),
            )
            self._append_step(llm_step)
            self._append_span(llm_trace)
            self._record_metrics(run_id, llm_step.latency_ms, llm_step.token_usage, 0)
            self._set_status(run_id, RunStatus.SUCCEEDED)
        except Exception as exc:
            error_step = TrajectoryStep(
                id=f"{run_id}-step-3",
                run_id=run_id,
                step_type=StepType.LLM,
                prompt=payload.prompt,
                output=f"live execution failed: {exc}",
                model=payload.model,
                temperature=0.0,
                latency_ms=0,
                token_usage=0,
                success=False,
            )
            error_trace = TraceSpan(
                run_id=run_id,
                span_id=f"span-{run_id}-3",
                parent_span_id=planner_trace.span_id,
                step_type=StepType.LLM,
                input={"prompt": payload.prompt, "model": payload.model},
                output={"output": error_step.output, "success": False},
                tool_name=None,
                latency_ms=0,
                token_usage=0,
                image_digest=payload.project_metadata.get("image_digest", "sha256:dev"),
                prompt_version=payload.project_metadata.get("prompt_version", "v1"),
            )
            self._append_step(error_step)
            self._append_span(error_trace)
            self._set_status(run_id, RunStatus.FAILED)

        memory_step = TrajectoryStep(
            id=f"{run_id}-step-4",
            run_id=run_id,
            step_type=StepType.MEMORY,
            prompt="Persist normalized artifacts",
            output="trajectory and spans persisted",
            model="recorder",
            temperature=0.0,
            latency_ms=1,
            token_usage=0,
            success=True,
        )
        memory_trace = TraceSpan(
            run_id=run_id,
            span_id=f"span-{run_id}-4",
            parent_span_id=planner_trace.span_id,
            step_type=StepType.MEMORY,
            input={"result": "persist"},
            output={"output": memory_step.output, "success": True},
            tool_name=None,
            latency_ms=memory_step.latency_ms,
            token_usage=0,
            image_digest=payload.project_metadata.get("image_digest", "sha256:dev"),
            prompt_version=payload.project_metadata.get("prompt_version", "v1"),
        )
        self._append_step(memory_step)
        self._append_span(memory_trace)
        self._record_metrics(run_id, memory_step.latency_ms, 0, 0)

    def _append_step(self, step: TrajectoryStep) -> None:
        state.append_trajectory_step(step)

    def _append_span(self, span: TraceSpan) -> None:
        state.append_trace_span(span)

    def _record_metrics(
        self,
        run_id: UUID,
        latency_ms: int,
        token_usage: int,
        tool_calls: int,
    ) -> None:
        with state.lock:
            run = state.runs.get(run_id)
            if not run:
                return
            run.latency_ms += latency_ms
            run.token_cost += token_usage
            run.tool_calls += tool_calls
            state.runs[run_id] = run
            state.save_run(run)

    def _set_status(self, run_id: UUID, status: RunStatus) -> None:
        with state.lock:
            run = state.runs.get(run_id)
            if run:
                run.status = status
                state.runs[run_id] = run
                state.save_run(run)

    def _coerce_id(self, run_id: str | UUID) -> UUID:
        if isinstance(run_id, UUID):
            return run_id
        return UUID(run_id)


orchestrator = RunOrchestrator()
