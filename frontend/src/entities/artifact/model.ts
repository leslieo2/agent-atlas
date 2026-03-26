import type { ArtifactFormat } from "@/src/shared/api/contract";

export interface ArtifactExport {
  artifactId: string;
  format: ArtifactFormat;
  runIds: string[];
  createdAt: string;
  path: string;
  sizeBytes: number;
}

export interface ExportArtifactInput {
  runIds: string[];
  format?: ArtifactFormat;
}
