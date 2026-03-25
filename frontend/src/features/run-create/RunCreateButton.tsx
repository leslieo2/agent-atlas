"use client";

import { Plus } from "lucide-react";
import type { RunRecord } from "@/src/entities/run/model";
import { useCreateRunMutation } from "@/src/entities/run/query";
import { Button } from "@/src/shared/ui/Button";

export function RunCreateButton({
  onCreated
}: {
  onCreated: (run: RunRecord) => void;
}) {
  const createRunMutation = useCreateRunMutation();

  return (
    <Button
      onClick={async () => {
        const run = await createRunMutation.mutateAsync({
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
