export interface DatasetRow {
  sampleId: string;
  input: string;
  expected?: string | null;
  tags?: string[];
}

export interface Dataset {
  name: string;
  rows: DatasetRow[];
}

export interface CreateDatasetInput {
  name: string;
  rows: DatasetRow[];
}
