"use client";

import { Download } from "lucide-react";
import { exportArtifact } from "@/src/entities/artifact/api";
import { Button } from "@/src/shared/ui/Button";

export function ArtifactExportActions({
  runId,
  onExported
}: {
  runId?: string;
  onExported: (message: string) => void;
}) {
  const exportLatestRun = async (format: "jsonl" | "parquet") => {
    if (!runId) return;

    const artifact = await exportArtifact({ runIds: [runId], format });
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

