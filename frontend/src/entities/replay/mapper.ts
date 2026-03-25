import type { ReplayResponse as ApiReplayResult } from "@/src/shared/api/contract";
import type { ReplayResult } from "./model";

export function mapReplay(result: ApiReplayResult): ReplayResult {
  return {
    replayId: result.replay_id,
    runId: result.run_id,
    stepId: result.step_id,
    baselineOutput: result.baseline_output,
    replayOutput: result.replay_output,
    diff: result.diff,
    updatedPrompt: result.updated_prompt,
    model: result.model,
    temperature: result.temperature,
    startedAt: result.started_at
  };
}
