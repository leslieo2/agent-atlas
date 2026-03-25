from __future__ import annotations

import difflib
import json
from uuid import uuid4

from app.modules.replays.application.ports import ReplayRuntimeRegistryPort
from app.modules.replays.domain.models import ReplayRequest, ReplayResult
from app.modules.runs.domain.models import RunRecord, RuntimeExecutionResult, TrajectoryStep
from app.modules.shared.domain.enums import StepType


class ReplayBaselineResolver:
    def resolve(self, steps: list[TrajectoryStep], step_id: str) -> TrajectoryStep:
        for step in steps:
            if step.id == step_id:
                if step.step_type == StepType.MEMORY:
                    raise ValueError(f"step '{step_id}' does not support replay")
                return step
        raise KeyError(f"step '{step_id}' not found")


class ReplayExecutor:
    def __init__(self, runner_registry: ReplayRuntimeRegistryPort) -> None:
        self.runner_registry = runner_registry

    def execute(
        self,
        request: ReplayRequest,
        baseline_step: TrajectoryStep,
        run: RunRecord,
    ) -> RuntimeExecutionResult:
        resolved_model = self._resolve_model(request, baseline_step, run)
        replay_prompt = self._build_prompt(request, baseline_step)
        runner = self.runner_registry.get_runner(run.agent_type)
        return runner.execute(run.agent_type, resolved_model, replay_prompt)

    def _resolve_model(
        self,
        request: ReplayRequest,
        baseline_step: TrajectoryStep,
        run: RunRecord,
    ) -> str:
        if request.model:
            return request.model

        baseline_model = (baseline_step.model or "").strip()
        if baseline_model and baseline_model.lower() not in {"n/a", "na"}:
            return baseline_model

        return run.model

    def _build_prompt(self, request: ReplayRequest, baseline_step: TrajectoryStep) -> str:
        replay_prompt = request.edited_prompt or baseline_step.prompt
        sections: list[str] = []

        if baseline_step.step_type == StepType.TOOL:
            tool_name = baseline_step.tool_name or "tool"
            sections.extend(
                [
                    f"Replay tool step '{tool_name}' in isolation.",
                    f"Edited tool input:\n{replay_prompt}",
                    f"Original tool output:\n{baseline_step.output}",
                ]
            )
        else:
            sections.append(replay_prompt)

        if request.rationale:
            sections.append(f"Replay rationale:\n{request.rationale}")

        if request.tool_overrides:
            sections.append(
                "Tool overrides:\n"
                f"{json.dumps(request.tool_overrides, ensure_ascii=False, sort_keys=True)}"
            )

        return "\n\n".join(sections)


class ReplayResultFactory:
    def build(
        self,
        request: ReplayRequest,
        baseline_step: TrajectoryStep,
        replay_result: RuntimeExecutionResult,
    ) -> ReplayResult:
        replay_prompt = request.edited_prompt or baseline_step.prompt
        model = request.model or baseline_step.model
        diff = "\n".join(
            difflib.unified_diff(
                baseline_step.output.splitlines(),
                replay_result.output.splitlines(),
                fromfile="baseline",
                tofile="replay",
                lineterm="",
            )
        )
        return ReplayResult(
            replay_id=uuid4(),
            run_id=request.run_id,
            step_id=request.step_id,
            baseline_output=baseline_step.output,
            replay_output=replay_result.output,
            diff=diff,
            updated_prompt=replay_prompt,
            model=model,
            temperature=baseline_step.temperature,
        )
