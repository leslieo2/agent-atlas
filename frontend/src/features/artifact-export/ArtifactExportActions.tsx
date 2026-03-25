"use client";

import { Download } from "lucide-react";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { Button } from "@/src/shared/ui/Button";

export function ArtifactExportActions({
  runId,
  onExported
}: {
  runId?: string;
  onExported: (message: string) => void;
}) {
  const exportArtifactMutation = useExportArtifactMutation();

  const exportLatestRun = async (format: "jsonl" | "parquet") => {
    if (!runId) return;

    const artifact = await exportArtifactMutation.mutateAsync({ runIds: [runId], format });
    onExported(`Exported ${artifact.artifactId} as ${format.toUpperCase()} (${artifact.sizeBytes} bytes)`);
  };

  return (
    <>
      <Button variant="ghost" onClick={() => exportLatestRun("jsonl")}>
        <Download size={14} /> Export JSONL
      </Button>
      <Button variant="ghost" onClick={() => exportLatestRun("parquet")}>
        <Download size={14} /> Export Parquet
      </Button>
    </>
  );
}
