export interface DatasetRow {
  sampleId: string;
  input: string;
  expected?: string | null;
  tags?: string[];
  slice?: string | null;
  source?: string | null;
  metadata?: Record<string, unknown> | null;
  exportEligible?: boolean | null;
}

export interface DatasetVersionRecord {
  datasetVersionId: string;
  datasetName: string;
  version?: string | null;
  createdAt: string;
  rowCount: number;
  rows: DatasetRow[];
}

export interface Dataset {
  name: string;
  description?: string | null;
  source?: string | null;
  createdAt: string;
  currentVersionId?: string | null;
  version?: string | null;
  rows: DatasetRow[];
  versions: DatasetVersionRecord[];
}

export interface CreateDatasetInput {
  name: string;
  description?: string | null;
  source?: string | null;
  version?: string | null;
  rows: DatasetRow[];
}

export interface CreateDatasetVersionInput {
  version?: string | null;
  rows: DatasetRow[];
}
