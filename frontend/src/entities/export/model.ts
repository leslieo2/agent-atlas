import type { ArtifactFormat, CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";

export interface ExportRecord {
  exportId: string;
  format: ArtifactFormat;
  createdAt: string;
  path: string;
  sizeBytes: number;
  rowCount: number;
  sourceExperimentId?: string | null;
  baselineExperimentId?: string | null;
  candidateExperimentId?: string | null;
  filtersSummary: Record<string, unknown>;
}

export interface CreateExportInput {
  experimentId?: string | null;
  baselineExperimentId?: string | null;
  candidateExperimentId?: string | null;
  datasetSampleIds?: string[] | null;
  judgements?: SampleJudgement[] | null;
  errorCodes?: string[] | null;
  compareOutcomes?: CompareOutcome[] | null;
  tags?: string[] | null;
  slices?: string[] | null;
  curationStatuses?: CurationStatus[] | null;
  exportEligible?: boolean | null;
  format?: ArtifactFormat;
}
