import type { TraceSpanResponse } from "@/src/shared/api/contract";
import type { TraceSpan } from "./model";

export function mapTraceSpan(span: TraceSpanResponse): TraceSpan {
  return {
    runId: span.run_id,
    spanId: span.span_id,
    parentSpanId: span.parent_span_id,
    stepType: span.step_type,
    input: span.input,
    output: span.output,
    toolName: span.tool_name,
    latencyMs: span.latency_ms,
    tokenUsage: span.token_usage,
    imageDigest: span.image_digest,
    promptVersion: span.prompt_version,
    receivedAt: span.received_at
  };
}
