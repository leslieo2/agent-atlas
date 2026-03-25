"use client";

import { Plus } from "lucide-react";
import { createRun } from "@/src/entities/run/api";
import type { RunRecord } from "@/src/entities/run/model";
import { Button } from "@/src/shared/ui/Button";

export function RunCreateButton({
  onCreated
}: {
  onCreated: (run: RunRecord) => void;
}) {
  return (
    <Button
      onClick={async () => {
        const run = await createRun({
          project: "workbench",
          dataset: "crm-v2",
          model: "gpt-4.1-mini",
          agentType: "openai-agents-sdk",
          inputSummary: "Manual run from dashboard",
          prompt: "Generate a shipping response",
          tags: ["ui"]
        });
        onCreated(run);
      }}
    >
      <Plus size={14} /> New Run
    </Button>
  );
}

