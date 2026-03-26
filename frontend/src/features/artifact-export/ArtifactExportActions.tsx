"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { getArtifactDownloadUrl } from "@/src/entities/artifact/api";
import { useExportArtifactMutation } from "@/src/entities/artifact/query";
import { Button } from "@/src/shared/ui/Button";
import { ArtifactExportFeedback } from "./ArtifactExportFeedback";

type FeedbackState =
  | {
      tone: "success" | "warn" | "error";
      title: string;
      detail?: string;
      downloadHref?: string;
      downloadLabel?: string;
    }
  | null;

function formatLabel(format: "jsonl" | "parquet") {
  return format === "jsonl" ? "JSONL" : "Parquet";
}

export function ArtifactExportActions({
  runIds,
  onExported
}: {
  runIds: string[];
  onExported?: () => void;
}) {
  const exportArtifactMutation = useExportArtifactMutation();
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const runCount = runIds.length;
  const countLabel = `${runCount} ${runCount === 1 ? "run" : "runs"}`;

  useEffect(() => {
    setFeedback(null);
  }, [runIds]);

  const exportFilteredRuns = async (format: "jsonl" | "parquet") => {
    if (!runCount) return;

    const formatName = formatLabel(format);
    setFeedback({
      tone: "warn",
      title: `Exporting ${countLabel} as ${formatName}...`,
      detail: "Preparing artifact and download link."
    });

    try {
      const artifact = await exportArtifactMutation.mutateAsync({ runIds, format });
      setFeedback({
        tone: "success",
        title: `Exported ${countLabel} as ${formatName}.`,
        detail: `${artifact.sizeBytes} bytes · current filter result`,
        downloadHref: getArtifactDownloadUrl(artifact.artifactId),
        downloadLabel: `Download ${formatName}`
      });
      onExported?.();
    } catch (error) {
      setFeedback({
        tone: "error",
        title: `${formatName} export failed.`,
        detail: error instanceof Error ? error.message : "Try again."
      });
    }
  };

  return (
    <div className="action-stack action-stack-right">
      <div className="toolbar">
        <Button variant="ghost" disabled={!runCount || exportArtifactMutation.isPending} onClick={() => exportFilteredRuns("jsonl")}>
          <Download size={14} /> {exportArtifactMutation.isPending ? "Exporting..." : `Export ${countLabel} as JSONL`}
        </Button>
        <Button
          variant="ghost"
          disabled={!runCount || exportArtifactMutation.isPending}
          onClick={() => exportFilteredRuns("parquet")}
        >
          <Download size={14} /> {exportArtifactMutation.isPending ? "Exporting..." : `Export ${countLabel} as Parquet`}
        </Button>
      </div>
      {feedback ? <ArtifactExportFeedback {...feedback} /> : null}
    </div>
  );
}
