import type { ArtifactFormat } from "@/src/shared/api/contract";

export interface ArtifactExport {
  artifactId: string;
  path: string;
  sizeBytes: number;
}

export interface ExportArtifactInput {
  runIds: string[];
  format?: ArtifactFormat;
}
