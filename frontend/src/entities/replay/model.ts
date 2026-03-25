export interface ReplayResult {
  replayId: string;
  runId: string;
  stepId: string;
  baselineOutput: string;
  replayOutput: string;
  diff: string;
  updatedPrompt?: string | null;
  model: string;
  temperature: number;
  startedAt: string;
}

export interface CreateReplayInput {
  runId: string;
  stepId: string;
  editedPrompt?: string;
  model?: string;
  toolOverrides?: Record<string, unknown>;
  rationale?: string;
}

