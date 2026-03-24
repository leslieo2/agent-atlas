from __future__ import annotations

import difflib
from uuid import uuid4

from app.db.state import state
from app.models.schemas import ReplayRequest, ReplayResult


class ReplayService:
    def replay_step(self, req: ReplayRequest) -> ReplayResult:
        with state.lock:
            steps = state.trajectory.get(req.run_id, [])
        baseline_step = None
        for step in steps:
            if step.id == req.step_id:
                baseline_step = step
                break
        if baseline_step is None:
            raise KeyError(f"step '{req.step_id}' not found")

        replay_prompt = req.edited_prompt or baseline_step.prompt
        model = req.model or baseline_step.model
        replay_output = (
            f"Replay output for step {req.step_id} with model={model}: "
            f"{replay_prompt[:60]} -> simulated policy-consistent response"
        )
        diff = "\n".join(
            difflib.unified_diff(
                baseline_step.output.splitlines(),
                replay_output.splitlines(),
                fromfile="baseline",
                tofile="replay",
                lineterm="",
            )
        )
        result = ReplayResult(
            replay_id=uuid4(),
            run_id=req.run_id,
            step_id=req.step_id,
            baseline_output=baseline_step.output,
            replay_output=replay_output,
            diff=diff,
            updated_prompt=replay_prompt,
            model=model,
            temperature=baseline_step.temperature,
        )
        with state.lock:
            state.replays[result.replay_id] = result
            state.save_replay(result)
        return result


replay_service = ReplayService()
