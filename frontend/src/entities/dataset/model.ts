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

export interface Dataset {
  name: string;
  description?: string | null;
  source?: string | null;
  version?: string | null;
  createdAt: string;
  rows: DatasetRow[];
}

export interface CreateDatasetInput {
  name: string;
  description?: string | null;
  source?: string | null;
  version?: string | null;
  rows: DatasetRow[];
}
