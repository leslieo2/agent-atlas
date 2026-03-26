import type { StepType } from "@/src/shared/api/contract";

export interface TrajectoryStep {
  id: string;
  runId: string;
  stepType: StepType;
  parentStepId?: string | null;
  prompt: string;
  output: string;
  model: string | null;
  temperature: number;
  latencyMs: number;
  tokenUsage: number;
  success: boolean;
  toolName?: string | null;
}
