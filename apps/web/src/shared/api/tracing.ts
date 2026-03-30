import type { TracingMetadata as ApiTracingMetadata } from "@/src/shared/api/contract";

export interface TracingRecord {
  backend: string;
  traceId?: string | null;
  traceUrl?: string | null;
  projectUrl?: string | null;
}

export function mapTracing(tracing?: ApiTracingMetadata | null): TracingRecord | null {
  if (!tracing) {
    return null;
  }

  return {
    backend: tracing.backend,
    traceId: tracing.trace_id ?? null,
    traceUrl: tracing.trace_url ?? null,
    projectUrl: tracing.project_url ?? null
  };
}
