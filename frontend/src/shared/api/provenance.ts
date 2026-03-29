import type { ProvenanceMetadata as ApiProvenanceMetadata } from "@/src/shared/api/contract";

export interface ProvenanceRecord {
  framework?: string | null;
  publishedAgentSnapshot?: Record<string, unknown> | null;
  artifactRef?: string | null;
  imageRef?: string | null;
  runnerBackend?: string | null;
  traceBackend?: string | null;
  evalJobId?: string | null;
  datasetSampleId?: string | null;
}

export function mapProvenance(provenance?: ApiProvenanceMetadata | null): ProvenanceRecord | null {
  if (!provenance) {
    return null;
  }

  return {
    framework: provenance.framework ?? null,
    publishedAgentSnapshot: provenance.published_agent_snapshot ?? null,
    artifactRef: provenance.artifact_ref ?? null,
    imageRef: provenance.image_ref ?? null,
    runnerBackend: provenance.runner_backend ?? null,
    traceBackend: provenance.trace_backend ?? null,
    evalJobId: provenance.eval_job_id ?? null,
    datasetSampleId: provenance.dataset_sample_id ?? null
  };
}
