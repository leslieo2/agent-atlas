import type { TrajectoryStep } from "./model";

type ApiTrajectoryStep = {
  id: string;
  run_id: string;
  step_type: "llm" | "tool" | "planner" | "memory";
  prompt: string;
  output: string;
  model: string;
  temperature: number;
  latency_ms: number;
  token_usage: number;
  success: boolean;
  tool_name?: string | null;
};

export function mapStep(step: ApiTrajectoryStep): TrajectoryStep {
  return {
    id: step.id,
    runId: step.run_id,
    stepType: step.step_type,
    prompt: step.prompt,
    output: step.output,
    model: step.model,
    temperature: step.temperature,
    latencyMs: step.latency_ms,
    tokenUsage: step.token_usage,
    success: step.success,
    toolName: step.tool_name
  };
}

export type { ApiTrajectoryStep };

