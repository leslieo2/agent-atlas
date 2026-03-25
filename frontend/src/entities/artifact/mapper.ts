import type { ArtifactMetadataResponse as ApiArtifact } from "@/src/shared/api/contract";
import type { ArtifactExport } from "./model";

export function mapArtifact(artifact: ApiArtifact): ArtifactExport {
  return {
    artifactId: artifact.artifact_id,
    path: artifact.path,
    sizeBytes: artifact.size_bytes
  };
}
