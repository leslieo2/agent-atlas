import type { StepType } from "@/src/shared/api/contract";

export interface TrajectoryStep {
  id: string;
  runId: string;
  stepType: StepType;
  prompt: string;
  output: string;
  model: string;
  temperature: number;
  latencyMs: number;
  tokenUsage: number;
  success: boolean;
  toolName?: string | null;
}
