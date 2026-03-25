"use client";

import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { useCreateRunMutation } from "@/src/shared/query/hooks";
import { Button } from "@/src/shared/ui/Button";

type Props = {
  candidate: TrajectoryStep | null;
  model: string;
  prompt: string;
  lastDiff: string;
  onUpdated: (value: string) => void;
};

export function PromoteReplayAction({ candidate, model, prompt, lastDiff, onUpdated }: Props) {
  const createRunMutation = useCreateRunMutation();

  return (
    <>
      <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(lastDiff)}>
        Save as candidate
      </Button>
      <Button
        variant="ghost"
        onClick={async () => {
          if (!candidate) return;
          const run = await createRunMutation.mutateAsync({
            project: "replay-candidate",
            dataset: "crm-v2",
            model,
            agentType: "openai-agents-sdk",
            inputSummary: `Replay candidate from ${candidate.id}`,
            prompt,
            tags: ["replay"]
          });
          onUpdated(`Promoted replay to new run ${run.runId}`);
        }}
      >
        Promote to new run
      </Button>
    </>
  );
}
