"use client";

import { ArrowUpDown } from "lucide-react";
import { Button } from "@/src/shared/ui/Button";

export function EvalRunActions({
  onRunEval,
  onExport
}: {
  onRunEval: () => Promise<void>;
  onExport: (format: "jsonl" | "parquet") => Promise<void>;
}) {
  return (
    <>
      <Button onClick={onRunEval}>Run batch eval</Button>
      <Button onClick={() => onExport("jsonl")}>Export JSONL</Button>
      <Button onClick={() => onExport("parquet")}>Export Parquet</Button>
      <Button onClick={onRunEval}>
        <ArrowUpDown size={14} /> Refresh metrics
      </Button>
    </>
  );
}

