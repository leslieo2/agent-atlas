import type { TrajectoryStepResponse as ApiTrajectoryStep } from "@/src/shared/api/contract";
import type { TrajectoryStep } from "./model";

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
