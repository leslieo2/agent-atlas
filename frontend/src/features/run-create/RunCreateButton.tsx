"use client";

import { Plus } from "lucide-react";
import { Button } from "@/src/shared/ui/Button";

export function RunCreateButton({
  datasetName,
  onCreated
}: {
  datasetName?: string;
  onCreated: () => void;
}) {
  return (
    <Button
      href={datasetName ? `/playground?dataset=${encodeURIComponent(datasetName)}` : "/playground"}
      onClick={onCreated}
    >
      <Plus size={14} /> New Run
    </Button>
  );
}
