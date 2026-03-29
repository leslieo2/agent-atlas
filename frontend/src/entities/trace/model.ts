import type { StepType } from "@/src/shared/api/contract";

export interface TraceSpan {
  runId: string;
  spanId: string;
  parentSpanId: string | null;
  stepType: StepType;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  toolName?: string | null;
  latencyMs: number;
  tokenUsage: number;
  imageDigest?: string | null;
  promptVersion?: string | null;
  traceBackend?: string | null;
  receivedAt: string;
}
