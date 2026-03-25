from __future__ import annotations

import difflib
from uuid import uuid4

from app.modules.replays.domain.models import ReplayRequest, ReplayResult
from app.modules.runs.domain.models import TrajectoryStep
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
    def execute(self, request: ReplayRequest, baseline_step: TrajectoryStep) -> str:
        replay_prompt = request.edited_prompt or baseline_step.prompt
        model = request.model or baseline_step.model
        return (
            f"Replay output for step {request.step_id} with model={model}: "
            f"{replay_prompt[:60]} -> simulated policy-consistent response"
        )


class ReplayResultFactory:
    def build(
        self,
        request: ReplayRequest,
        baseline_step: TrajectoryStep,
        replay_output: str,
    ) -> ReplayResult:
        replay_prompt = request.edited_prompt or baseline_step.prompt
        model = request.model or baseline_step.model
        diff = "\n".join(
            difflib.unified_diff(
                baseline_step.output.splitlines(),
                replay_output.splitlines(),
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
            replay_output=replay_output,
            diff=diff,
            updated_prompt=replay_prompt,
            model=model,
            temperature=baseline_step.temperature,
        )
