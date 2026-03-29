import type { ObservabilityMetadata as ApiObservabilityMetadata } from "@/src/shared/api/contract";

export interface ObservabilityRecord {
  backend: string;
  traceId?: string | null;
  traceUrl?: string | null;
  projectUrl?: string | null;
}

export function mapObservability(observability?: ApiObservabilityMetadata | null): ObservabilityRecord | null {
  if (!observability) {
    return null;
  }

  return {
    backend: observability.backend,
    traceId: observability.trace_id ?? null,
    traceUrl: observability.trace_url ?? null,
    projectUrl: observability.project_url ?? null
  };
}
