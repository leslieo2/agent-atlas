import type { ArtifactFormat, CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";

export interface ExportRecord {
  exportId: string;
  format: ArtifactFormat;
  createdAt: string;
  path: string;
  sizeBytes: number;
  rowCount: number;
  sourceEvalJobId?: string | null;
  baselineEvalJobId?: string | null;
  candidateEvalJobId?: string | null;
  filtersSummary: Record<string, unknown>;
}

export interface CreateExportInput {
  evalJobId?: string | null;
  baselineEvalJobId?: string | null;
  candidateEvalJobId?: string | null;
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
