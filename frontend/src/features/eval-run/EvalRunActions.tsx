"use client";

import { ArrowUpDown } from "lucide-react";
import { Button } from "@/src/shared/ui/Button";

export function EvalRunActions({
  onRunEval,
  onExport,
  disabled = false
}: {
  onRunEval: () => Promise<void>;
  onExport: (format: "jsonl" | "parquet") => Promise<void>;
  disabled?: boolean;
}) {
  return (
    <>
      <Button onClick={onRunEval} disabled={disabled}>
        Run batch eval
      </Button>
      <Button onClick={() => onExport("jsonl")} disabled={disabled}>
        Export JSONL
      </Button>
      <Button onClick={() => onExport("parquet")} disabled={disabled}>
        Export Parquet
      </Button>
      <Button onClick={onRunEval} disabled={disabled}>
        <ArrowUpDown size={14} /> Refresh metrics
      </Button>
    </>
  );
}
