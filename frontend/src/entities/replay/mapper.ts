import type { ReplayResult } from "./model";

type ApiReplayResult = {
  replay_id: string;
  run_id: string;
  step_id: string;
  baseline_output: string;
  replay_output: string;
  diff: string;
  updated_prompt?: string | null;
  model: string;
  temperature: number;
  started_at: string;
};

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

export type { ApiReplayResult };

