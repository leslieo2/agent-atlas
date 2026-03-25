export interface Dataset {
  name: string;
  rows: Array<{ sampleId: string; input: string }>;
}

export interface CreateDatasetInput {
  name: string;
  rows: Array<{ sampleId: string; input: string; expected?: string | null; tags?: string[] }>;
}

