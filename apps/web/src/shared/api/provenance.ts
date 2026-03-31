import type { ProvenanceMetadata as ApiProvenanceMetadata } from "@/src/shared/api/contract";

export interface ProvenanceRecord {
  framework?: string | null;
  frameworkVersion?: string | null;
  publishedAgentSnapshot?: Record<string, unknown> | null;
  artifactRef?: string | null;
  imageRef?: string | null;
  runnerBackend?: string | null;
  executorBackend?: string | null;
  traceBackend?: string | null;
  experimentId?: string | null;
  datasetVersionId?: string | null;
  datasetSampleId?: string | null;
}

export function mapProvenance(provenance?: ApiProvenanceMetadata | null): ProvenanceRecord | null {
  if (!provenance) {
    return null;
  }

  return {
    framework: provenance.framework ?? null,
    frameworkVersion: provenance.framework_version ?? null,
    publishedAgentSnapshot: provenance.published_agent_snapshot ?? null,
    artifactRef: provenance.artifact_ref ?? null,
    imageRef: provenance.image_ref ?? null,
    runnerBackend: provenance.runner_backend ?? null,
    executorBackend: provenance.executor_backend ?? null,
    traceBackend: provenance.trace_backend ?? null,
    experimentId: provenance.experiment_id ?? null,
    datasetVersionId: provenance.dataset_version_id ?? null,
    datasetSampleId: provenance.dataset_sample_id ?? null
  };
}
