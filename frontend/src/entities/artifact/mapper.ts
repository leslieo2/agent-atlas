import type { ArtifactExport } from "./model";

type ApiArtifact = {
  artifact_id: string;
  path: string;
  size_bytes: number;
};

export function mapArtifact(artifact: ApiArtifact): ArtifactExport {
  return {
    artifactId: artifact.artifact_id,
    path: artifact.path,
    sizeBytes: artifact.size_bytes
  };
}

export type { ApiArtifact };

