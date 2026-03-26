import type { ArtifactExport } from "./model";

export function formatArtifactDate(date: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(date));
}

export function formatArtifactSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  const kib = sizeBytes / 1024;
  if (kib < 1024) {
    return `${kib.toFixed(1)} KB`;
  }

  return `${(kib / 1024).toFixed(1)} MB`;
}

export function formatArtifactRunCount(artifact: ArtifactExport) {
  return `${artifact.runIds.length} ${artifact.runIds.length === 1 ? "run" : "runs"}`;
}
