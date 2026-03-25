export interface TrajectoryStep {
  id: string;
  runId: string;
  stepType: "llm" | "tool" | "planner" | "memory";
  prompt: string;
  output: string;
  model: string;
  temperature: number;
  latencyMs: number;
  tokenUsage: number;
  success: boolean;
  toolName?: string | null;
}

