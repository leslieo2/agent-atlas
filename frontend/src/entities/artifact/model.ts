export interface ArtifactExport {
  artifactId: string;
  path: string;
  sizeBytes: number;
}

export interface ExportArtifactInput {
  runIds: string[];
  format?: "jsonl" | "parquet";
}

